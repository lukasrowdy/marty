"""Orders, line items, and the small parsers (money, quantity, dates) everything else shares."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def parse_money(text) -> Decimal | None:
    """'$1,234.56' -> Decimal('1234.56'). Returns None for blanks or text with no number."""
    if text is None:
        return None
    if isinstance(text, (int, float, Decimal)):
        return cents(Decimal(str(text)))
    s = str(text).strip()
    if not s:
        return None
    negative = s.startswith("-") or s.startswith("(") or "-$" in s
    m = re.search(r"(\d[\d,]*(?:\.\d+)?|\.\d+)", s)
    if not m:
        return None
    try:
        value = Decimal(m.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    return cents(-value if negative else value)


def parse_qty(text) -> Decimal:
    """'Qty: 2' -> 2. Anything unreadable counts as 1."""
    if text is None:
        return Decimal(1)
    if isinstance(text, (int, float, Decimal)):
        return Decimal(str(text))
    m = re.search(r"\d+(?:\.\d+)?", str(text))
    if not m:
        return Decimal(1)
    value = Decimal(m.group(0))
    return value if value > 0 else Decimal(1)


MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

# One regex that finds the date shapes the three retailers print. Used in sites.toml as {date}.
DATE_RE = (r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
           r"|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})")


def parse_date(text) -> date | None:
    if text is None:
        return None
    if isinstance(text, date):
        return text
    s = str(text).strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        year = int(m.group(3))
        year = year + 2000 if year < 100 else year
        return date(year, int(m.group(1)), int(m.group(2)))
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})", s)
    if m and m.group(1)[:3].lower() in MONTHS:
        return date(int(m.group(3)), MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
    return None


@dataclass
class LineItem:
    name: str
    qty: Decimal = Decimal(1)
    unit_price: Decimal | None = None
    line_total: Decimal | None = None
    category: str = ""
    # Line total plus this line's share of the order's tax, shipping, fees and discounts.
    allocated_total: Decimal | None = None
    # True for the synthetic "tax/fees/unmatched" line added when an order can't be allocated cleanly.
    is_adjustment: bool = False


@dataclass
class Order:
    retailer: str
    order_number: str
    date: date
    order_total: Decimal | None
    items: list[LineItem] = field(default_factory=list)
    url: str = ""

    @property
    def items_sum(self) -> Decimal:
        return sum((i.line_total or Decimal(0) for i in self.items if not i.is_adjustment), Decimal(0))

    def to_json(self) -> dict:
        def num(v):
            return None if v is None else str(v)
        return {
            "retailer": self.retailer,
            "order_number": self.order_number,
            "date": self.date.isoformat(),
            "order_total": num(self.order_total),
            "url": self.url,
            "items": [{"name": i.name, "qty": num(i.qty), "unit_price": num(i.unit_price),
                       "line_total": num(i.line_total)} for i in self.items if not i.is_adjustment],
        }

    @classmethod
    def from_json(cls, d: dict) -> "Order":
        when = parse_date(d.get("date"))
        if when is None:
            raise ValueError(f"order {d.get('order_number')!r} has no readable date: {d.get('date')!r}")
        items = []
        for it in d.get("items", []):
            qty = parse_qty(it.get("qty"))
            unit = parse_money(it.get("unit_price"))
            line = parse_money(it.get("line_total"))
            if line is None and unit is not None:
                line = cents(unit * qty)
            if unit is None and line is not None:
                unit = cents(line / qty)
            items.append(LineItem(name=str(it.get("name", "")).strip(), qty=qty, unit_price=unit, line_total=line))
        return cls(retailer=d["retailer"], order_number=str(d["order_number"]), date=when,
                   order_total=parse_money(d.get("order_total")), items=items, url=d.get("url", ""))


def today() -> date:
    return datetime.now().date()
