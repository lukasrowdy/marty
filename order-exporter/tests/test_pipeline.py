"""Pipeline tests: tagging, allocation, outputs, weekly summary, dry run. No browser needed.

    python -m unittest discover -s tests -v        (from the order-exporter folder)
"""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import export_orders  # noqa: E402
from exporter import CATEGORIES, canonical_retailer, outputs, process, weekly  # noqa: E402
from exporter.config import load_config, load_sites  # noqa: E402
from exporter.models import LineItem, Order, parse_date, parse_money  # noqa: E402
from exporter.rules import categorize, load_rules  # noqa: E402

D = Decimal


def order(items, total, retailer="Walmart", num="1", when=date(2026, 11, 3)):
    return Order(retailer=retailer, order_number=num, date=when, order_total=None if total is None else D(total),
                 items=[LineItem(name=n, qty=D(q), unit_price=D(p), line_total=D(p) * D(q)) for n, q, p in items])


class ParseTests(unittest.TestCase):
    def test_money(self):
        self.assertEqual(parse_money("$1,234.56"), D("1234.56"))
        self.assertEqual(parse_money("-$3.00"), D("-3.00"))
        self.assertIsNone(parse_money(""))
        self.assertIsNone(parse_money("free"))

    def test_dates(self):
        for s in ("November 3, 2026", "Nov 03, 2026", "Nov. 3 2026", "11/03/2026", "11/3/26", "2026-11-03"):
            self.assertEqual(parse_date(s), date(2026, 11, 3), s)
        self.assertIsNone(parse_date("Delivered Tuesday"))

    def test_retailer_names(self):
        self.assertEqual(canonical_retailer("samsclub"), "Sam's Club")
        self.assertEqual(canonical_retailer("SAM'S CLUB"), "Sam's Club")
        with self.assertRaises(ValueError):
            canonical_retailer("Target")


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(ROOT / "category_rules.csv")

    def test_shipped_rules_file(self):
        cases = {
            ("Bounty Select-A-Size Paper Towels, 12 Double Rolls", "Amazon"): "Household",
            ("Great Value Large White Eggs, 18 Count", "Walmart"): "Grocery",
            ("Great Value Whole Vitamin D Milk, 1 Gallon", "Walmart"): "Grocery",
            ("Nature Made Vitamin D3 Softgels", "Amazon"): "Household",
            ("HP 67XL Black High-yield Ink Cartridge", "Amazon"): "Business/Materials",
            ("GRK Fasteners 2x4 Framing Screws, 100 ct", "Amazon"): "Business/Materials",
            ("Nail polish remover", "Walmart"): "Household",
            ("Member's Mark Rotisserie Chicken", "Sam's Club"): "Grocery",
            ("Anker USB-C Cable", "Amazon"): "Other",
            ("Eggplant", "Walmart"): "Grocery",
        }
        for (name, retailer), want in cases.items():
            self.assertEqual(categorize(name, retailer, self.rules), want, name)

    def test_first_match_wins_and_retailer_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.csv"
            p.write_text("category,match,pattern,retailer,note\n"
                         "# comment row,,,,\n"
                         "Business/Materials,contains,tape,Amazon,\n"
                         "Household,word,tape,,\n"
                         "Grocery,regex,^fresh\\b,,\n", encoding="utf-8")
            rules = load_rules(p)
            self.assertEqual(categorize("Packing Tape", "Amazon", rules), "Business/Materials")
            self.assertEqual(categorize("Packing Tape", "Walmart", rules), "Household")
            self.assertEqual(categorize("Fresh Basil", "Walmart", rules), "Grocery")
            self.assertEqual(categorize("Refresh Wipes", "Walmart", rules), "Other")

    def test_bad_category_is_reported_with_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.csv"
            p.write_text("category,match,pattern\nGroceries,word,milk\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2"):
                load_rules(p)


class AllocationTests(unittest.TestCase):
    def test_tax_spread_adds_up_to_the_cent(self):
        o = order([("a", 1, "10.00"), ("b", 3, "3.33"), ("c", 1, "0.01")], "21.43")
        self.assertIsNone(process.allocate(o, "allocate", D(25)))
        self.assertEqual(sum(i.allocated_total for i in o.items), D("21.43"))
        self.assertTrue(all(i.allocated_total >= i.line_total for i in o.items))

    def test_large_gap_becomes_its_own_line(self):
        o = order([("a", 1, "10.00")], "50.00")
        warning = process.allocate(o, "allocate", D(25))
        self.assertIn("adjustment", warning)
        self.assertEqual(o.items[0].allocated_total, D("10.00"))
        self.assertTrue(o.items[-1].is_adjustment)
        self.assertEqual(o.items[-1].allocated_total, D("40.00"))
        self.assertEqual(o.items[-1].category, "Other")

    def test_discount_reduces_lines(self):
        o = order([("a", 1, "10.00"), ("b", 1, "10.00")], "18.00")
        process.allocate(o, "allocate", D(25))
        self.assertEqual([i.allocated_total for i in o.items], [D("9.00"), D("9.00")])

    def test_ignore_mode_and_missing_total(self):
        o = order([("a", 1, "10.00")], "12.00")
        process.allocate(o, "ignore", D(25))
        self.assertEqual(o.items[0].allocated_total, D("10.00"))
        o = order([("a", 1, "10.00")], None)
        self.assertIn("no order total", process.allocate(o, "allocate", D(25)))
        self.assertEqual(o.items[0].allocated_total, D("10.00"))

    def test_reallocating_is_stable(self):
        o = order([("a", 1, "10.00")], "50.00")
        process.allocate(o, "allocate", D(25))
        process.allocate(o, "allocate", D(25))
        self.assertEqual(sum(1 for i in o.items if i.is_adjustment), 1)


class WeeklyTests(unittest.TestCase):
    def test_columns_are_fixed(self):
        cols = weekly.columns()
        self.assertEqual(len(cols), 3 + 3 * 5 + 5 + 5)
        self.assertEqual(cols[:3], ["Week Start", "Week End", "Full Week Covered"])
        self.assertEqual(cols[-5:], ["Grocery Budget", "Grocery Spent", "Grocery Remaining",
                                     "Grocery % of Budget", "Over Budget"])
        # A week with no orders still has every column.
        rows = weekly.build([], [date(2026, 11, 2)], date(2026, 11, 2), date(2026, 11, 8), 0, D("100"))
        self.assertEqual(list(rows[0].keys()), cols)
        self.assertEqual(rows[0]["Total Spend"], D(0))

    def test_week_start_and_budget(self):
        self.assertEqual(weekly.week_start(date(2026, 11, 7), 0), date(2026, 11, 2))  # Saturday -> Monday
        self.assertEqual(weekly.week_start(date(2026, 11, 7), 6), date(2026, 11, 1))  # Sunday start
        o = order([("Milk", 1, "120.00")], "120.00")
        o.items[0].category = "Grocery"
        process.allocate(o, "allocate", D(25))
        rows = weekly.build([o], [date(2026, 11, 2)], date(2026, 11, 2), date(2026, 11, 8), 0, D("100"))
        r = rows[0]
        self.assertEqual(r["Walmart Grocery"], D("120.00"))
        self.assertEqual(r["Grocery Remaining"], D("-20.00"))
        self.assertEqual(r["Grocery % of Budget"], "120.0%")
        self.assertEqual(r["Over Budget"], "Yes")
        self.assertEqual(r["Full Week Covered"], "Yes")


class DryRunTests(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = export_orders.main(list(args))
        return code, buf.getvalue()

    def test_dry_run_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            code, text = self.run_cli("--dry-run", "--out", str(out))
            self.assertEqual(code, 0, text)
            files = {p.name.split("_20")[0]: p for p in out.iterdir()}
            self.assertEqual(set(files), {"orders", "ledger_import", "weekly_summary"})
            self.assertEqual(len(list(out.glob("orders_*.xlsx"))), 1)

            items = list(csv.DictReader(io.StringIO(next(out.glob("orders_*.csv")).read_text(encoding="utf-8-sig"))))
            self.assertEqual(list(items[0].keys())[:8], ["Date", "Retailer", "Order Number", "Item", "Qty",
                                                         "Unit Price", "Line Total", "Order Total"])
            self.assertEqual({r["Retailer"] for r in items}, {"Amazon", "Walmart", "Sam's Club"})
            self.assertTrue({r["Category"] for r in items} <= set(CATEGORIES))

            ledger_path = next(out.glob("ledger_import_*.csv"))
            raw = ledger_path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "Ledger CSV should have no BOM by default")
            ledger = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
            self.assertEqual(list(ledger[0].keys()), ["date", "description", "amount", "account", "category"])
            self.assertTrue(all(D(r["amount"]) < 0 for r in ledger))
            sample = json.loads((ROOT / "sample" / "sample_orders.json").read_text(encoding="utf-8"))
            charged = sum(D(o["order_total"]) for o in sample["orders"])
            self.assertEqual(-sum(D(r["amount"]) for r in ledger), charged, "ledger must tie to order totals")

            summary = list(csv.reader(io.StringIO(next(out.glob("weekly_summary_*.csv")).read_text(encoding="utf-8-sig"))))
            self.assertEqual(summary[0], weekly.columns())
            self.assertEqual(len(summary), 1 + 3)  # three weeks in the sample
            total_col = summary[0].index("Total Spend")
            self.assertEqual(sum(D(r[total_col]) for r in summary[1:]), charged)

            from openpyxl import load_workbook
            wb = load_workbook(next(out.glob("orders_*.xlsx")))
            self.assertEqual(wb.sheetnames, ["Line Items", "Orders", "Weekly Summary"])
            self.assertEqual(wb["Line Items"].max_row, len(items) + 1)

    def test_dry_run_never_writes_ledger_state(self):
        cfg = load_config()
        state = cfg.state_dir / "ledger_exported.txt"
        before = state.read_bytes() if state.exists() else None
        with tempfile.TemporaryDirectory() as tmp:
            self.run_cli("--dry-run", "--out", tmp)
        self.assertEqual(state.read_bytes() if state.exists() else None, before)

    def test_ledger_skips_lines_already_exported(self):
        cfg = load_config()
        o = order([("Milk", 1, "3.00"), ("Eggs", 1, "4.00")], "7.00")
        process.prepare([o], load_rules(cfg.rules_file), "allocate", D(25))
        rows, keys = outputs.ledger_rows([o], cfg, set())
        self.assertEqual(len(rows), 2)
        rows2, _ = outputs.ledger_rows([o], cfg, {keys[0]})
        self.assertEqual([r[1] for r in rows2], ["Walmart: Eggs"])

    def test_last_week_window(self):
        cfg = load_config()
        args = export_orders.parse_args(["--last-week"])
        since, until = export_orders.date_window(args, cfg, None)
        self.assertEqual(since.weekday(), cfg.week_starts_on)
        self.assertEqual((until - since).days, 6)
        self.assertLess(until, date.today())


class VendorChoiceTests(unittest.TestCase):
    def test_choices(self):
        pick = export_orders.parse_vendor_choice
        default = ["amazon", "walmart"]
        self.assertEqual(pick("", default), default)
        self.assertEqual(pick("all", default), ["amazon", "walmart", "samsclub"])
        self.assertEqual(pick("3,1", default), ["amazon", "samsclub"])  # always in menu order
        self.assertEqual(pick("1 3", default), ["amazon", "samsclub"])
        self.assertEqual(pick("Sam's Club, walmart", default), ["walmart", "samsclub"])
        self.assertEqual(pick("sams", default), ["samsclub"])
        self.assertEqual(pick("wal; 1", default), ["amazon", "walmart"])
        self.assertEqual(pick("a", default), ["amazon"])  # a unique start of a name is enough
        for bad in ("4", "target", "x", "0"):
            with self.assertRaises(ValueError, msg=bad):
                pick(bad, default)

    def test_prompt_asks_again_after_a_bad_answer(self):
        answers = iter(["target", "2"])
        said = []
        got = export_orders.choose_vendors(["amazon"], ask=lambda m: next(answers), say=said.append)
        self.assertEqual(got, ["walmart"])
        self.assertTrue(any("target" in s for s in said))

    def test_no_prompt_when_not_interactive(self):
        # The test runner's stdin is not a console, so a dry run must never block on the vendor question.
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(export_orders.main(["--dry-run", "--out", tmp]), 0)
            self.assertNotIn("Which vendors", buf.getvalue())


class SitesFileTests(unittest.TestCase):
    """The shipped sites.toml patterns against URL and text shapes the retailers use."""

    def setUp(self):
        self.sites = load_sites(ROOT / "sites.toml")

    def m(self, key, field, s):
        import re
        from exporter.scraper import first_match
        value = self.sites[key][field]
        if isinstance(value, list):
            return first_match(value, s)
        hit = re.search(value, s)
        return hit.group(1) if hit else None

    def test_order_links(self):
        self.assertEqual(self.m("amazon", "order_link_regex",
                                "https://www.amazon.com/gp/your-account/order-details?ref=x&orderID=113-5550192-3388104"),
                         "113-5550192-3388104")
        self.assertEqual(self.m("amazon", "order_link_regex",
                                "https://www.amazon.com/your-orders/order-details?orderID=D01-1234567-1234567"),
                         "D01-1234567-1234567")
        self.assertEqual(self.m("walmart", "order_link_regex", "https://www.walmart.com/orders/2000138-77016652"),
                         "2000138-77016652")
        self.assertIsNone(self.m("walmart", "order_link_regex", "https://www.walmart.com/orders"))
        self.assertEqual(self.m("samsclub", "order_link_regex", "https://www.samsclub.com/orders/8004588120"),
                         "8004588120")

    def test_product_links(self):
        self.assertEqual(self.m("amazon", "product_link_regex", "https://www.amazon.com/gp/product/B00GRANOLA/ref=x"),
                         "B00GRANOLA")
        self.assertEqual(self.m("walmart", "product_link_regex",
                                "https://www.walmart.com/ip/Great-Value-Eggs-18-Count/145051970?x=1"), "145051970")
        self.assertEqual(self.m("samsclub", "product_link_regex",
                                "https://www.samsclub.com/p/members-mark-towels/prod24440190?xid=plp"), "prod24440190")

    def test_dates_and_totals(self):
        self.assertEqual(parse_date(self.m("amazon", "date_patterns", "Ordered on November 4, 2026  Order# 1")),
                         date(2026, 11, 4))
        self.assertEqual(parse_date(self.m("walmart", "date_patterns", "Nov 03, 2026 order\nOrder# 2")),
                         date(2026, 11, 3))
        text = "Subtotal $22.05\nTotal savings $3.00\nTaxes $0.44\nTotal $22.49"
        self.assertEqual(self.m("walmart", "total_patterns", text), "22.49")
        self.assertEqual(self.m("amazon", "total_patterns", "Item(s) Subtotal: $52.66\nGrand Total: $56.48"), "56.48")


if __name__ == "__main__":
    unittest.main()
