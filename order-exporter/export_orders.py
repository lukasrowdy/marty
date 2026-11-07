#!/usr/bin/env python3
"""Export Amazon, Walmart and Sam's Club order history to CSV, Excel, a Ledger import file and a weekly summary.

    python export_orders.py --dry-run                 test everything with the sample file, no browser, no login
    python export_orders.py                           asks which vendors, then the last 30 days (lookback_days)
    python export_orders.py --last-week               the previous full week; the weekly-paste routine
    python export_orders.py --since 2026-01-01        from a date to today
    python export_orders.py --retailers amazon,walmart
    python export_orders.py --from-json output\\raw_orders_....json   re-tag a saved scrape without logging in

Chrome opens with one tab per vendor, each on its sign-in page. You log in yourself on every tab, press
Enter once, and the script reads each vendor's order history in turn. No passwords are typed, read or stored, and the browser session is thrown
away when the run ends. Nothing is sent anywhere: all output stays in the output folder.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from exporter import RETAILERS, canonical_retailer
from exporter import outputs, process, weekly
from exporter.config import HERE, load_config, load_sites
from exporter.models import Order, parse_date, today
from exporter.rules import load_rules

SAMPLE = HERE / "sample" / "sample_orders.json"


def _date(s: str) -> date:
    d = parse_date(s)
    if d is None:
        raise argparse.ArgumentTypeError(f"not a date: {s!r} (use YYYY-MM-DD)")
    return d


def parse_args(argv):
    p = argparse.ArgumentParser(description="Export retail order history (Amazon, Walmart, Sam's Club).")
    p.add_argument("--dry-run", action="store_true",
                   help="use the sample file instead of the browser; writes to output/dry-run and remembers nothing")
    p.add_argument("--sample", type=Path, default=SAMPLE, help="sample file for --dry-run")
    p.add_argument("--from-json", type=Path, help="re-process a raw_orders_*.json saved by an earlier run")
    p.add_argument("--retailers", help="comma list: amazon,walmart,samsclub (default: config.toml)")
    p.add_argument("--since", type=_date, help="first order date to include (YYYY-MM-DD)")
    p.add_argument("--until", type=_date, help="last order date to include (default today)")
    p.add_argument("--last-week", action="store_true", help="the previous full week (week_starts_on in config)")
    p.add_argument("--week", type=_date, help="the full week containing this date")
    p.add_argument("--out", type=Path, help="output folder (default from config.toml)")
    p.add_argument("--config", type=Path, help="config file (default config.toml)")
    p.add_argument("--ledger-all", action="store_true",
                   help="put every line in the Ledger file, even ones exported on an earlier run")
    p.add_argument("--debug", action="store_true", help="save a snapshot of every order page to the debug folder")
    p.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--browser-path", help=argparse.SUPPRESS)
    return p.parse_args(argv)


def load_json_orders(path: Path) -> list[Order]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = data["orders"] if isinstance(data, dict) else data
    orders = []
    for d in rows:
        d = dict(d)
        d["retailer"] = canonical_retailer(d["retailer"])
        orders.append(Order.from_json(d))
    return orders


def date_window(args, cfg, sample_orders: list[Order] | None) -> tuple[date, date]:
    if args.last_week:
        ws = weekly.week_start(today(), cfg.week_starts_on) - timedelta(days=7)
        return ws, ws + timedelta(days=6)
    if args.week:
        ws = weekly.week_start(args.week, cfg.week_starts_on)
        return ws, ws + timedelta(days=6)
    if sample_orders and not args.since and not args.until:
        return min(o.date for o in sample_orders), max(o.date for o in sample_orders)
    until = args.until or today()
    since = args.since or (until - timedelta(days=cfg.lookback_days))
    if since > until:
        raise SystemExit(f"--since {since} is after --until {until}")
    return since, until


def parse_vendor_choice(text: str, default: list[str]) -> list[str]:
    """'1,3' / 'amazon, sams' / 'all' / '' (= default) -> retailer keys in menu order. ValueError if unclear."""
    keys = list(RETAILERS)
    t = text.strip()
    if not t:
        return list(default)
    if t.lower() == "all":
        return keys
    picked: set[str] = set()
    for part in [p.strip() for p in t.replace(";", ",").split(",") if p.strip()]:
        tokens = part.split() if all(tok.isdigit() for tok in part.split()) else [part]  # "1 3" works too
        for tok in tokens:
            if tok.isdigit():
                if not 1 <= int(tok) <= len(keys):
                    raise ValueError(f"there is no vendor number {tok}")
                picked.add(keys[int(tok) - 1])
                continue
            norm = tok.lower().replace("'", "").replace("\u2019", "").replace(" ", "")
            hits = [k for k in keys if k.startswith(norm) or
                    RETAILERS[k].lower().replace("'", "").replace(" ", "").startswith(norm)]
            if len(hits) != 1:
                raise ValueError(f"{tok!r} doesn't match one vendor; use a number or a name from the list")
            picked.add(hits[0])
    return [k for k in keys if k in picked]


def choose_vendors(default: list[str], ask=input, say=print) -> list[str]:
    keys = list(RETAILERS)
    menu = "\n".join(f"    {n}) {RETAILERS[k]}" for n, k in enumerate(keys, start=1))
    default_names = ", ".join(RETAILERS[k] for k in default)
    while True:
        answer = ask(f"\nWhich vendors should I export?\n{menu}\n"
                     f"  Type numbers or names separated by commas (like 1,3), or all.\n"
                     f"  Press Enter for: {default_names}\n  > ")
        try:
            picked = parse_vendor_choice(answer, default)
        except ValueError as e:
            say(f"  {e}")
            continue
        if picked:
            say(f"  Exporting: {', '.join(RETAILERS[k] for k in picked)}")
            return picked
        say("  Pick at least one vendor.")


def scrape(cfg, retailers: list[str], since: date, until: date, args) -> list[Order]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed. Run setup.bat (or: pip install -r requirements.txt)")
    from exporter.scraper import Scraper, launch_browser, login_all

    sites = load_sites(cfg.sites_file)
    all_orders: list[Order] = []
    with sync_playwright() as pw:
        browser, context = launch_browser(pw, cfg.browser_channel, headless=args.headless,
                                          executable_path=args.browser_path)
        try:
            # One tab per vendor, all opened together, so you log in to everything in one sitting.
            scrapers = [Scraper(context, sites[key], since, until, delay=cfg.delay_seconds,
                                max_orders=cfg.max_orders_per_retailer, max_pages=cfg.max_list_pages,
                                debug_dir=cfg.debug_dir, save_all_debug=args.debug) for key in retailers]
            try:
                login_all(scrapers)
            except KeyboardInterrupt:
                print("\n  stopped by you before the export started")
                return all_orders
            for s in scrapers:
                print(f"\n=== {s.site['name']} ({since} to {until}) ===")
                try:
                    s.run()
                except KeyboardInterrupt:
                    print(f"\n  stopped by you; keeping the {len(s.orders)} {s.site['name']} order(s) read so far")
                    all_orders += s.orders
                    break
                print(f"  {s.site['name']}: {len(s.orders)} order(s) in range")
                all_orders += s.orders
                s.close()
        finally:
            context.close()  # the session (cookies included) is discarded here
            browser.close()
    return all_orders


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    args = parse_args(sys.argv[1:] if argv is None else argv)
    cfg = load_config(args.config)
    retailers = cfg.retailers
    if args.retailers:
        retailers = [canonical_retailer(r) for r in args.retailers.split(",") if r.strip()]
        retailers = [k for k, v in RETAILERS.items() if v in retailers]
    rules = load_rules(cfg.rules_file)  # fail early on a broken rules file, before any login
    live = not args.dry_run and not args.from_json
    if live and not args.retailers and cfg.ask_for_vendors and sys.stdin.isatty():
        retailers = choose_vendors(retailers)
    names = {RETAILERS[k] for k in retailers}

    source_orders = None
    if args.dry_run:
        source_orders = load_json_orders(args.from_json or args.sample)
        print(f"DRY RUN: reading {args.from_json or args.sample} (no browser, no login, nothing remembered)")
    elif args.from_json:
        source_orders = load_json_orders(args.from_json)
        print(f"Reading saved orders from {args.from_json}")

    since, until = date_window(args, cfg, source_orders if (args.dry_run or args.from_json) else None)
    out_dir = args.out or (cfg.output_dir / "dry-run" if args.dry_run else cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{since.isoformat()}_to_{until.isoformat()}"

    if source_orders is None:
        source_orders = scrape(cfg, retailers, since, until, args)
        raw_path = out_dir / f"raw_orders_{stamp}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump({"orders": [o.to_json() for o in source_orders]}, f, indent=2)
        print(f"\nSaved the raw scrape to {raw_path} (re-run with --from-json to re-tag without logging in)")

    orders = process.filter_orders([o for o in source_orders if o.retailer in names], since, until)
    warnings = process.prepare(orders, rules, cfg.order_adjustments, cfg.max_adjustment_percent)

    weeks = weekly.weeks_in(since, until, cfg.week_starts_on)
    week_rows = weekly.build(orders, weeks, since, until, cfg.week_starts_on, cfg.weekly_grocery_budget)

    items_csv = out_dir / f"orders_{stamp}.csv"
    xlsx = out_dir / f"orders_{stamp}.xlsx"
    # The Ledger file is named for the moment it was made, so a batch you have not imported yet is never
    # overwritten by a later run (which would leave out the lines already in that batch).
    ledger_csv = out_dir / f"ledger_import_{datetime.now():%Y-%m-%d_%H%M%S}.csv"
    weekly_csv = out_dir / f"weekly_summary_{stamp}.csv"

    n_items = outputs.write_items_csv(orders, items_csv)
    outputs.write_weekly_csv(week_rows, weekly_csv)
    outputs.write_xlsx(orders, week_rows, xlsx)

    remember = cfg.ledger_skip_already_exported and not args.dry_run and not args.ledger_all
    state_file = cfg.state_dir / "ledger_exported.txt"
    skip = outputs.load_exported(state_file) if remember else set()
    ledger, keys = outputs.ledger_rows(orders, cfg, skip)
    if ledger or args.dry_run:
        outputs.write_ledger_csv(ledger, ledger_csv, cfg.ledger_bom)
    if cfg.ledger_skip_already_exported and not args.dry_run:
        outputs.save_exported(state_file, keys)

    print(f"\n{len(orders)} order(s), {n_items} line(s), {since} to {until}")
    for r in sorted(names):
        print(f"  {r}: {sum(1 for o in orders if o.retailer == r)} order(s)")
    if warnings:
        print(f"\n{len(warnings)} thing(s) to check:")
        for w in warnings:
            print(f"  - {w}")
    skipped_note = f" ({len(skip & set(outputs.line_key(o, n, i.name) for o in orders for n, i in enumerate(o.items)))}" \
                   f" already-exported line(s) left out)" if skip else ""
    print("\nWrote:")
    print(f"  {items_csv}")
    print(f"  {xlsx}")
    if ledger or args.dry_run:
        print(f"  {ledger_csv}  [{len(ledger)} line(s) to import{skipped_note}]")
    else:
        print(f"  (no Ledger file: no new lines since the last export{skipped_note})")
    print(f"  {weekly_csv}")
    if week_rows:
        last = week_rows[-1]
        print(f"\nWeek of {last['Week Start']}: grocery {last['Grocery Spent']:.2f} of budget "
              f"{last['Grocery Budget']:.2f} (remaining {last['Grocery Remaining']:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
