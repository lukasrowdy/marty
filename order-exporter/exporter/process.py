"""Turn scraped orders into tagged line items whose amounts add up to what you were charged."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from .models import LineItem, Order, cents
from .rules import Rule, categorize

ADJUSTMENT_NAME = "Order adjustment (tax, fees, discounts or items not read)"


def filter_orders(orders: list[Order], since: date, until: date) -> list[Order]:
    seen: set[tuple[str, str]] = set()
    out = []
    for o in sorted(orders, key=lambda o: (o.date, o.retailer, o.order_number)):
        key = (o.retailer, o.order_number)
        if key in seen or not (since <= o.date <= until):
            continue
        seen.add(key)
        out.append(o)
    return out


def tag(orders: list[Order], rules: list[Rule]) -> None:
    for o in orders:
        for item in o.items:
            if not item.is_adjustment:
                item.category = categorize(item.name, o.retailer, rules)


def allocate(order: Order, mode: str, max_percent: Decimal) -> str | None:
    """Fill allocated_total on every item. Returns a warning string when something needs a look.

    allocate: the difference between the order total and the sum of line totals (tax, shipping, fees,
              discounts) is spread across the lines in proportion to their line totals, so each line
              carries its own tax and the lines add up to the order total to the cent. When the difference
              is larger than max_percent of the order, or a line has no price, the difference is NOT spread;
              it becomes one separate "Order adjustment" line tagged Other, so a missed item never inflates
              the items that were read.
    ignore:   allocated_total is just the line total.
    """
    items = [i for i in order.items if not i.is_adjustment]
    order.items = items
    for i in items:
        i.allocated_total = i.line_total
    if mode != "allocate":
        return None
    if order.order_total is None:
        return f"{order.retailer} {order.order_number}: no order total found; amounts are item prices only"

    priced = [i for i in items if i.line_total is not None]
    diff = order.order_total - order.items_sum
    if diff == 0:
        return None

    unpriced = len(priced) != len(items)
    too_big = order.order_total != 0 and abs(diff) / abs(order.order_total) * 100 > max_percent
    base = sum((i.line_total for i in priced), Decimal(0))
    if unpriced or too_big or base <= 0:
        order.items.append(LineItem(name=ADJUSTMENT_NAME, qty=Decimal(1), unit_price=diff, line_total=diff,
                                    category="Other", allocated_total=diff, is_adjustment=True))
        why = "a line had no price" if unpriced else (
            "no priced lines" if base <= 0 else f"difference is over {max_percent}% of the order")
        return (f"{order.retailer} {order.order_number}: order total {order.order_total} vs items {order.items_sum} "
                f"({why}); added a separate adjustment line of {diff}")

    running = Decimal(0)
    for i in priced:
        share = cents(diff * i.line_total / base)
        i.allocated_total = i.line_total + share
        running += share
    leftover = diff - running
    if leftover:
        biggest = max(priced, key=lambda i: i.line_total)
        biggest.allocated_total += leftover
    return None


def prepare(orders: list[Order], rules: list[Rule], mode: str, max_percent: Decimal) -> list[str]:
    tag(orders, rules)
    warnings = []
    for o in orders:
        w = allocate(o, mode, max_percent)
        if w:
            warnings.append(w)
        if not o.items:
            warnings.append(f"{o.retailer} {o.order_number} ({o.date}): no line items were read")
    return warnings
