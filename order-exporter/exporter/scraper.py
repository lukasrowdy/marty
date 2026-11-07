"""Reads order history out of a browser window you have logged into yourself.

One engine serves all three retailers; what differs per site (URLs, link shapes, labels) lives in
sites.toml so a page change can usually be fixed there without touching code.

How a retailer is read:
  1. Open the order-history page and wait for you to log in and press Enter.
  2. Collect links to order-detail pages from the list, newest first, paging with Next / Load more.
  3. Open each order's detail page in a second tab and read the date, total and line items.
  4. Stop once a whole page of orders is older than the start date.

Line items are found by product links (each site's product_link_regex). For each product the engine
climbs to the largest page block that holds that product and no other, then reads the price and quantity
from that block's text. Recommendation carousels are skipped.

Nothing here types or stores credentials. The browser context is fresh for each run and discarded.
"""
from __future__ import annotations

import random
import re
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .models import LineItem, Order, cents, parse_date, parse_money, parse_qty

EXTRACT_JS = r"""
(args) => {
  const prodRe = new RegExp(args.productHrefRegex);
  const roots = [];
  for (const sel of args.itemsRootSelectors || []) {
    try { document.querySelectorAll(sel).forEach(el => roots.push(el)); } catch (e) {}
  }
  if (!roots.length) roots.push(document.body);
  const excluded = (el) => {
    for (const sel of args.excludeSelectors || []) {
      try { if (el.closest(sel)) return true; } catch (e) {}
    }
    return false;
  };
  const keyOf = (a) => { const m = a.href.match(prodRe); return (m && m[1]) ? m[1] : a.href.split(/[?#]/)[0]; };
  const isProduct = (a) => prodRe.test(a.href) && !excluded(a);
  const groups = new Map();
  for (const root of roots) {
    for (const a of root.querySelectorAll('a[href]')) {
      if (!isProduct(a)) continue;
      const k = keyOf(a);
      if (!groups.has(k)) groups.set(k, []);
      if (!groups.get(k).includes(a)) groups.get(k).push(a);
    }
  }
  const keysIn = (el) => {
    const s = new Set();
    for (const a of el.querySelectorAll('a[href]')) if (isProduct(a)) s.add(keyOf(a));
    return s;
  };
  const stopRe = args.blockStopRegex ? new RegExp(args.blockStopRegex, 'i') : null;
  const clean = (t) => (t || '').replace(/[ \t ]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
  const items = [];
  for (const [k, links] of groups) {
    let title = '';
    for (const a of links) { const t = clean(a.innerText).replace(/\n/g, ' '); if (t.length > title.length) title = t; }
    if (!title) {
      for (const a of links) {
        const img = a.querySelector('img[alt]');
        const t = clean(a.getAttribute('aria-label') || a.title || (img && img.alt) || '');
        if (t.length > title.length) title = t;
      }
    }
    // Start at the element holding all of this product's links, then climb while the block
    // still holds only this product and has not reached the order summary.
    let block = links[0];
    while (block.parentElement && !links.every(a => block.contains(a))) block = block.parentElement;
    let el = block.parentElement;
    while (el && el !== document.body && !roots.includes(el)) {
      if (keysIn(el).size > 1) break;
      const txt = el.innerText || '';
      if (stopRe && stopRe.test(txt)) break;
      if (txt.length > 3000) break;
      block = el;
      el = el.parentElement;
    }
    let qtyText = '';
    if (args.qtySelector) {
      try { const q = block.querySelector(args.qtySelector); if (q) qtyText = clean(q.innerText); } catch (e) {}
    }
    items.push({key: k, title: title, text: clean(block.innerText), qty_text: qtyText});
  }
  return {items: items, text: document.body ? document.body.innerText : '', url: location.href};
}
"""

LINKS_JS = r"""
(re) => {
  const r = new RegExp(re);
  const out = [], seen = new Set();
  for (const a of document.querySelectorAll('a[href]')) {
    const m = a.href.match(r);
    if (m && m[1] && !seen.has(m[1])) { seen.add(m[1]); out.push([m[1], a.href]); }
  }
  return out;
}
"""

PRICE_RE = re.compile(r"(-)?\$\s?(\d[\d,]*\.\d{2})")
QTY_RES = [
    re.compile(r"(?i)\b(?:qty|quantity)\b\s*[:x]?\s*(\d+(?:\.\d+)?)"),
    re.compile(r"(?im)^\s*(\d+)\s+of\s*:"),
    re.compile(r"(?i)\b(\d+)\s*(?:x|×)\s*\$"),
]
EACH_RE = re.compile(r"^\s*(?:/\s*|per\s+|\s)(?:ea\b|each\b)", re.I)
MEASURE_RE = re.compile(r"^\s*(?:/|per)\s*(?:oz|lb|lbs|ct|count|fl|kg|g|ml|l|ft|sq|pk|pack|unit)\b", re.I)
IGNORE_BEFORE_RE = re.compile(r"(?i)(?:was|list|reg\.?|regular|save|saved|savings|off|discount|msrp|strikethrough)"
                              r"[\s:]*$")
IGNORE_AFTER_RE = re.compile(r"(?i)^\s*(?:off|savings|saved|in savings)\b")


def parse_item(raw: dict, price_is_line_total: bool) -> LineItem | None:
    """Price and quantity from one product block's text. Pure function, unit-tested without a browser."""
    name = " ".join((raw.get("title") or "").split())
    text = raw.get("text") or ""
    if not name:
        return None
    qty = None
    if raw.get("qty_text") and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", raw["qty_text"]):
        qty = parse_qty(raw["qty_text"])
    if qty is None:
        for rx in QTY_RES:
            m = rx.search(text)
            if m:
                qty = parse_qty(m.group(1))
                break
    qty = qty or Decimal(1)

    each, plain = None, []
    for m in PRICE_RE.finditer(text):
        before, after = text[max(0, m.start() - 14):m.start()], text[m.end():m.end() + 14]
        if m.group(1) or IGNORE_BEFORE_RE.search(before) or IGNORE_AFTER_RE.search(after):
            continue
        value = parse_money(m.group(2))
        if EACH_RE.search(after):
            each = each if each is not None else value
        elif MEASURE_RE.search(after):
            continue
        else:
            plain.append(value)

    if each is not None:
        unit = each
        expected = cents(unit * qty)
        line = next((p for p in plain if p == expected), expected)
    elif plain:
        if price_is_line_total:
            line = plain[0]
            unit = cents(line / qty)
        else:
            unit = plain[0]
            line = cents(unit * qty)
    else:
        unit = line = None
    return LineItem(name=name, qty=qty, unit_price=unit, line_total=line)


def first_match(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1) if m.groups() else m.group(0)
    return None


def parse_detail(data: dict, site: dict, order_id: str) -> tuple[Order | None, str]:
    """(order, note). order is None when the page is not an order (cancelled, unreadable date)."""
    text = data.get("text") or ""
    if first_match(site.get("skip_order_patterns", []), text):
        return None, "skipped (cancelled)"
    when = parse_date(first_match(site.get("date_patterns", []), text))
    if when is None:
        return None, "no order date found on the page"
    total = parse_money(first_match(site.get("total_patterns", []), text))
    items = []
    for raw in data.get("items", []):
        item = parse_item(raw, bool(site.get("price_is_line_total", False)))
        if item and len(item.name) >= 3:
            items.append(item)
    return Order(retailer=site["name"], order_number=order_id, date=when, order_total=total, items=items,
                 url=data.get("url", "")), ""


def expand_list_urls(site: dict, since: date, until: date) -> list[str]:
    urls = []
    for u in site["list_urls"]:
        if "{year}" in u:
            urls += [u.replace("{year}", str(y)) for y in range(until.year, since.year - 1, -1)]
        else:
            urls.append(u)
    return urls


class Scraper:
    def __init__(self, context, site: dict, since: date, until: date, *, delay: float = 2.0,
                 max_orders: int = 300, max_pages: int = 30, debug_dir: Path | None = None,
                 save_all_debug: bool = False, ask: Callable[[str], str] = input, log: Callable[[str], None] = print):
        self.ctx, self.site, self.since, self.until = context, site, since, until
        self.delay, self.max_orders, self.max_pages = delay, max_orders, max_pages
        self.debug_dir, self.save_all_debug, self.ask, self.log = debug_dir, save_all_debug, ask, log
        self.orders: list[Order] = []
        self.list_page = context.new_page()
        self.detail_page = context.new_page()

    # -- helpers -------------------------------------------------------------------------------------
    def _settle(self, page, timeout: int = 8000) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            pass  # busy pages never go idle; what has loaded is enough

    def _pause(self) -> None:
        if self.delay > 0:
            time.sleep(self.delay + random.uniform(0, self.delay / 2))

    def _needs_human(self, page) -> str | None:
        url = page.url.lower()
        if any(s in url for s in self.site.get("login_url_markers", [])):
            return "sign in"
        try:
            text = page.inner_text("body", timeout=3000)
        except Exception:
            return None
        if first_match(self.site.get("blocked_patterns", []), text):
            return "solve the check (robot / press-and-hold / captcha)"
        return None

    def _human_gate(self, page) -> None:
        for _ in range(3):
            need = self._needs_human(page)
            if not need:
                return
            self.ask(f"\n  {self.site['name']}: please {need} in the browser window, then press Enter here... ")
            self._settle(page)

    def _save_debug(self, name: str, page) -> None:
        if not self.debug_dir:
            return
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:80]
        try:
            (self.debug_dir / f"{self.site['key']}_{safe}.html").write_text(page.content(), encoding="utf-8")
            (self.debug_dir / f"{self.site['key']}_{safe}.txt").write_text(page.inner_text("body"), encoding="utf-8")
        except Exception as e:  # a debug snapshot must never stop the export
            self.log(f"    (could not save debug snapshot: {e})")

    def _order_links(self) -> list[tuple[str, str]]:
        links = [tuple(x) for x in self.list_page.evaluate(LINKS_JS, self.site["order_link_regex"])]
        tmpl, id_re = self.site.get("order_url_template"), self.site.get("order_id_text_regex")
        if tmpl and id_re:
            have = {i for i, _ in links}
            text = self.list_page.inner_text("body")
            for m in re.finditer(id_re, text):
                if m.group(1) not in have:
                    have.add(m.group(1))
                    links.append((m.group(1), tmpl.replace("{id}", m.group(1))))
        return links

    def _next_page(self) -> bool:
        for sel in self.site.get("next_selectors", []):
            try:
                loc = self.list_page.locator(sel).first
                if loc.count() and loc.is_visible() and loc.is_enabled():
                    loc.scroll_into_view_if_needed(timeout=3000)
                    loc.click(timeout=5000)
                    self._settle(self.list_page)
                    return True
            except Exception:
                continue
        return False

    # -- the work ------------------------------------------------------------------------------------
    def wait_for_login(self) -> None:
        start = self.site.get("login_url") or expand_list_urls(self.site, self.since, self.until)[0]
        self.list_page.goto(start, wait_until="domcontentloaded")
        self.list_page.bring_to_front()
        self.ask(f"\n>>> {self.site['name']}: log in in the browser window (and pass any check it shows).\n"
                 f"    When you can see your order history, come back here and press Enter... ")

    def read_order(self, order_id: str, url: str) -> Order | None:
        page = self.detail_page
        page.goto(url, wait_until="domcontentloaded")
        self._settle(page)
        self._human_gate(page)
        args = {
            "productHrefRegex": self.site["product_link_regex"],
            "itemsRootSelectors": self.site.get("items_root_selectors", []),
            "excludeSelectors": self.site.get("exclude_selectors", []),
            "qtySelector": self.site.get("qty_selector", ""),
            "blockStopRegex": self.site.get("block_stop_regex", ""),
        }
        data = page.evaluate(EXTRACT_JS, args)
        order, note = parse_detail(data, self.site, order_id)
        if order is None:
            self.log(f"    {order_id}: {note}")
            if "date" in note:
                self._save_debug(order_id, page)
            return None
        if not order.items or self.save_all_debug:
            self._save_debug(order_id, page)
        return order

    def run(self) -> list[Order]:
        # Kept on self so a run cut short with Ctrl+C still hands back what it read.
        self.orders: list[Order] = []
        orders = self.orders
        seen: set[str] = set()
        visited = 0
        for list_url in expand_list_urls(self.site, self.since, self.until):
            self.list_page.goto(list_url, wait_until="domcontentloaded")
            self._settle(self.list_page)
            self._human_gate(self.list_page)
            for page_no in range(self.max_pages):
                links = [(i, u) for i, u in self._order_links() if i not in seen]
                if not links:
                    if page_no == 0:
                        self.log(f"  no order links found on {list_url}")
                        self._save_debug("order_list", self.list_page)
                    break
                dates = []
                for order_id, url in links:
                    seen.add(order_id)
                    if visited >= self.max_orders:
                        self.log(f"  stopped at max_orders_per_retailer = {self.max_orders}")
                        return orders
                    visited += 1
                    self._pause()
                    try:
                        order = self.read_order(order_id, url)
                    except Exception as e:
                        self.log(f"    {order_id}: could not read ({type(e).__name__}: {e})")
                        continue
                    if order is None:
                        continue
                    dates.append(order.date)
                    if self.since <= order.date <= self.until:
                        orders.append(order)
                        self.log(f"    {order.date}  {order_id}  {len(order.items)} item(s)  total {order.order_total}")
                if dates and max(dates) < self.since:
                    break  # this whole page is older than the start date; lists are newest first
                if not self._next_page():
                    break
        return orders


def launch_browser(playwright, channel: str, headless: bool = False, executable_path: str | None = None,
                   log: Callable[[str], None] = print):
    """Fresh, throwaway browser. channel: msedge (built into Windows 11), chrome, or chromium (bundled)."""
    kwargs: dict = {"headless": headless, "args": ["--disable-blink-features=AutomationControlled"]}
    if executable_path:
        kwargs["executable_path"] = executable_path
    elif channel in ("msedge", "chrome"):
        kwargs["channel"] = channel
    try:
        browser = playwright.chromium.launch(**kwargs)
    except Exception as e:
        if "channel" not in kwargs:
            raise RuntimeError(f"could not start the browser ({e}). Run: python -m playwright install chromium") from e
        log(f"  could not start {channel} ({str(e).splitlines()[0]}); trying Playwright's bundled Chromium")
        kwargs.pop("channel")
        try:
            browser = playwright.chromium.launch(**kwargs)
        except Exception as e2:
            raise RuntimeError("could not start any browser. Install Edge or Chrome, or run: "
                               "python -m playwright install chromium") from e2
    context = browser.new_context(no_viewport=not headless, locale="en-US")
    return browser, context
