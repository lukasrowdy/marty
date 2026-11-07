"""Weekly summary: one row per week, the same columns every time, so it pastes into the same Google Sheet."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from . import CATEGORIES, RETAILERS
from .models import Order


def week_start(d: date, start_day: int) -> date:
    return d - timedelta(days=(d.weekday() - start_day) % 7)


def weeks_in(since: date, until: date, start_day: int) -> list[date]:
    out, w = [], week_start(since, start_day)
    while w <= until:
        out.append(w)
        w += timedelta(days=7)
    return out


def columns() -> list[str]:
    cols = ["Week Start", "Week End", "Full Week Covered"]
    for r in RETAILERS.values():
        cols += [f"{r} {c}" for c in CATEGORIES] + [f"{r} Total"]
    cols += [f"Total {c}" for c in CATEGORIES] + ["Total Spend"]
    cols += ["Grocery Budget", "Grocery Spent", "Grocery Remaining", "Grocery % of Budget", "Over Budget"]
    return cols


def amount(item) -> Decimal:
    if item.allocated_total is not None:
        return item.allocated_total
    return item.line_total or Decimal(0)


def build(orders: list[Order], weeks: list[date], since: date, until: date, start_day: int,
          budget: Decimal) -> list[dict]:
    rows = []
    for ws in weeks:
        we = ws + timedelta(days=6)
        cell: dict[tuple[str, str], Decimal] = {(r, c): Decimal(0) for r in RETAILERS.values() for c in CATEGORIES}
        for o in orders:
            if ws <= o.date <= we:
                for i in o.items:
                    cell[(o.retailer, i.category or "Other")] += amount(i)
        row: dict[str, object] = {"Week Start": ws.isoformat(), "Week End": we.isoformat(),
                                  "Full Week Covered": "Yes" if since <= ws and we <= until else "No"}
        for r in RETAILERS.values():
            for c in CATEGORIES:
                row[f"{r} {c}"] = cell[(r, c)]
            row[f"{r} Total"] = sum((cell[(r, c)] for c in CATEGORIES), Decimal(0))
        for c in CATEGORIES:
            row[f"Total {c}"] = sum((cell[(r, c)] for r in RETAILERS.values()), Decimal(0))
        row["Total Spend"] = sum((row[f"Total {c}"] for c in CATEGORIES), Decimal(0))
        grocery = row["Total Grocery"]
        row["Grocery Budget"] = budget
        row["Grocery Spent"] = grocery
        row["Grocery Remaining"] = budget - grocery
        row["Grocery % of Budget"] = f"{(grocery / budget * 100):.1f}%" if budget > 0 else ""
        row["Over Budget"] = ("Yes" if grocery > budget else "No") if budget > 0 else ""
        rows.append(row)
    return rows
