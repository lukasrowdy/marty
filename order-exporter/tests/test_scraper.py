"""Scraper tests: drive a real (headless) browser against local pages shaped like each retailer's order pages.

These prove the engine works: login pause, link collection, Next / Load more paging, stopping at the start
date, item blocks, quantities, unit vs line prices, strikethrough and per-pound prices, carousels skipped.
They do NOT prove the live sites still look like this; only a real run can show that.

Skipped when Playwright or a browser is not available. Set ORDER_EXPORTER_TEST_BROWSER to a Chromium
executable to choose one.
"""
from __future__ import annotations

import os
import sys
import threading
import unittest
from datetime import date
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from exporter.config import load_sites  # noqa: E402
from exporter.scraper import Scraper, launch_browser, parse_item  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
D = Decimal


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        parts = u.path.strip("/").split("/")
        name = None
        if u.path == "/amazon/list":
            name = "amazon_list_1.html"
        elif u.path == "/amazon/list2":
            name = "amazon_list_2.html"
        elif u.path.endswith("/order-details"):
            name = f"amazon_order_{parse_qs(u.query).get('orderID', [''])[0]}.html"
        elif parts[:2] == ["walmart", "orders"]:
            name = "walmart_list.html" if len(parts) == 2 else f"walmart_order_{parts[2]}.html"
        elif parts[:2] == ["sams", "orders"]:
            name = "samsclub_list.html" if len(parts) == 2 else f"samsclub_order_{parts[2]}.html"
        path = FIX / name if name else None
        if path and path.is_file():
            body, code = path.read_bytes(), 200
        else:
            body, code = b"<html><body>Page not found</body></html>", 404
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _browser_path():
    env = os.environ.get("ORDER_EXPORTER_TEST_BROWSER")
    if env:
        return env
    return "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None


class ParseItemTests(unittest.TestCase):
    def test_unit_price_site(self):
        it = parse_item({"title": "Widget", "text": "Widget\n$18.99", "qty_text": "2"}, False)
        self.assertEqual((it.qty, it.unit_price, it.line_total), (D(2), D("18.99"), D("37.98")))

    def test_line_price_site_with_each_and_was(self):
        it = parse_item({"title": "Bacon", "text": "Bacon\nQty 2\n$13.96\n$6.98/ea\nWas $8.48"}, True)
        self.assertEqual((it.qty, it.unit_price, it.line_total), (D(2), D("6.98"), D("13.96")))

    def test_per_pound_price_is_not_the_line(self):
        it = parse_item({"title": "Potatoes", "text": "Potatoes\n$0.79/lb\nQty 1\n$3.97"}, True)
        self.assertEqual(it.line_total, D("3.97"))

    def test_no_price(self):
        it = parse_item({"title": "Gift", "text": "Gift\nQty 1"}, True)
        self.assertIsNone(it.line_total)


class ScraperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise unittest.SkipTest("playwright not installed")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.pw = sync_playwright().start()
        try:
            cls.browser, cls.context = launch_browser(cls.pw, "msedge", headless=True,
                                                      executable_path=_browser_path(), log=lambda s: None)
        except Exception as e:
            cls.pw.stop()
            cls.server.shutdown()
            raise unittest.SkipTest(f"no browser available: {e}")
        cls.sites = load_sites(ROOT / "sites.toml")

    @classmethod
    def tearDownClass(cls):
        cls.context.close()
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()

    def scrape(self, key, **overrides):
        site = dict(self.sites[key])
        site.update(overrides)
        prompts = []
        s = Scraper(self.context, site, date(2026, 10, 15), date(2026, 11, 7), delay=0,
                    ask=lambda msg: prompts.append(msg) or "", log=lambda m: None)
        s.wait_for_login()
        orders = s.run()
        s.list_page.close()
        s.detail_page.close()
        self.assertEqual(len(prompts), 1, "only the login prompt should be shown")
        return {o.order_number: o for o in orders}

    def items(self, order):
        return {i.name: (i.qty, i.unit_price, i.line_total) for i in order.items}

    def test_amazon(self):
        orders = self.scrape("amazon", login_url=None, list_urls=[self.base + "/amazon/list"])
        self.assertEqual(set(orders), {"113-5550192-3388104", "113-9917320-1184456"})  # September order left out
        o = orders["113-5550192-3388104"]
        self.assertEqual(o.date, date(2026, 11, 4))
        self.assertEqual(o.order_total, D("56.48"))
        self.assertEqual(self.items(o), {
            "Nature Valley Crunchy Granola Bars, 49 Count": (D(1), D("14.68"), D("14.68")),
            "Brita Standard Water Filter Replacements, 6 Count": (D(2), D("18.99"), D("37.98")),
        })
        self.assertEqual(orders["113-9917320-1184456"].order_total, D("41.27"))
        self.assertEqual(len(orders["113-9917320-1184456"].items), 2)

    def test_walmart_order_numbers_from_text(self):
        orders = self.scrape("walmart", login_url=None, list_urls=[self.base + "/walmart/orders"],
                             order_url_template=self.base + "/walmart/orders/{id}")
        self.assertEqual(set(orders), {"2000138-77016652"})
        o = orders["2000138-77016652"]
        self.assertEqual(o.date, date(2026, 11, 3))
        self.assertEqual(o.order_total, D("22.49"))
        self.assertEqual(self.items(o), {
            "Great Value Large White Eggs, 18 Count": (D(1), D("4.12"), D("4.12")),
            "Oscar Mayer Thick Cut Bacon, 16 oz": (D(2), D("6.98"), D("13.96")),
            "Fresh Russet Potatoes, 5 lb Bag": (D(1), D("3.97"), D("3.97")),
        })

    def test_samsclub_load_more(self):
        orders = self.scrape("samsclub", login_url=None, list_urls=[self.base + "/sams/orders"],
                             order_link_regex=r"/sams/orders/(\d+)")
        self.assertEqual(set(orders), {"8004588120"})
        o = orders["8004588120"]
        self.assertEqual(o.date, date(2026, 11, 6))
        self.assertEqual(o.order_total, D("65.65"))
        self.assertEqual(self.items(o), {
            "Member's Mark Boneless Skinless Chicken Breasts, 6 lb": (D(2), D("19.88"), D("39.76")),
            "Member's Mark Commercial Laundry Detergent, 300 loads": (D(1), D("23.98"), D("23.98")),
        })


if __name__ == "__main__":
    unittest.main()
