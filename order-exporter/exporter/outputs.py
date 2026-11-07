"""Writers: combined line-item CSV, Excel workbook, Ledger import CSV, weekly summary CSV."""
from __future__ import annotations

import csv
import hashlib
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import weekly
from .config import Config
from .models import Order

ITEM_COLUMNS = ["Date", "Retailer", "Order Number", "Item", "Qty", "Unit Price", "Line Total", "Order Total",
                "Category", "Amount Incl Tax/Fees"]
LEDGER_COLUMNS = ["date", "description", "amount", "account", "category"]
MONEY_FMT = '"$"#,##0.00;[Red]-"$"#,##0.00'


def _num(v: Decimal | None) -> str:
    return "" if v is None else f"{v:.2f}"


def _qty(v: Decimal) -> str:
    return str(int(v)) if v == v.to_integral_value() else str(v.normalize())


def item_rows(orders: list[Order]) -> list[list[str]]:
    rows = []
    for o in orders:
        for i in o.items:
            rows.append([o.date.isoformat(), o.retailer, o.order_number, i.name, _qty(i.qty), _num(i.unit_price),
                         _num(i.line_total), _num(o.order_total), i.category, _num(i.allocated_total)])
    return rows


def write_items_csv(orders: list[Order], path: Path) -> int:
    rows = item_rows(orders)
    # utf-8-sig: Excel on Windows needs the BOM to show accented and symbol characters correctly.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(ITEM_COLUMNS)
        w.writerows(rows)
    return len(rows)


def write_weekly_csv(rows: list[dict], path: Path) -> None:
    cols = weekly.columns()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([_num(r[c]) if isinstance(r[c], Decimal) else r[c] for c in cols])


def line_key(o: Order, index: int, name: str) -> str:
    """Stable id for one ledger line, used to skip lines already exported on an earlier run."""
    raw = f"{o.retailer}|{o.order_number}|{index}|{name}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def ledger_rows(orders: list[Order], cfg: Config, skip: set[str]) -> tuple[list[list[str]], list[str]]:
    rows, keys = [], []
    for o in orders:
        for n, i in enumerate(o.items):
            amt = i.allocated_total if i.allocated_total is not None else i.line_total
            if amt is None or amt == 0:
                continue
            k = line_key(o, n, i.name)
            if k in skip:
                continue
            desc = cfg.ledger_description.format(retailer=o.retailer, item=i.name, order=o.order_number,
                                                 qty=_qty(i.qty), category=i.category)
            rows.append([o.date.strftime(cfg.ledger_date_format), " ".join(desc.split()), f"{-amt:.2f}",
                         cfg.ledger_accounts.get(o.retailer, "Credit Card"),
                         cfg.ledger_category_names.get(i.category, i.category)])
            keys.append(k)
    return rows, keys


def write_ledger_csv(rows: list[list[str]], path: Path, bom: bool) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig" if bom else "utf-8") as f:
        w = csv.writer(f)
        w.writerow(LEDGER_COLUMNS)
        w.writerows(rows)


def load_exported(state_file: Path) -> set[str]:
    if not state_file.exists():
        return set()
    return {ln.strip() for ln in state_file.read_text(encoding="utf-8").splitlines() if ln.strip()}


def save_exported(state_file: Path, keys: list[str]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "a", encoding="utf-8") as f:
        for k in keys:
            f.write(k + "\n")


def _sheet(ws, header: list[str], rows: list[list], money_cols: set[int], widths: dict[int, int]) -> None:
    ws.append(header)
    for c in range(1, len(header) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="305496")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for r in rows:
        ws.append(r)
    for c in money_cols:
        for row in ws.iter_rows(min_row=2, min_col=c, max_col=c):
            row[0].number_format = MONEY_FMT
    for c in range(1, len(header) + 1):
        ws.column_dimensions[get_column_letter(c)].width = widths.get(c, max(10, min(28, len(header[c - 1]) + 2)))
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(header))}{len(rows) + 1}"


def write_xlsx(orders: list[Order], weekly_rows: list[dict], path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Line Items"
    rows = []
    for o in orders:
        for i in o.items:
            rows.append([o.date, o.retailer, o.order_number, i.name, float(i.qty),
                         None if i.unit_price is None else float(i.unit_price),
                         None if i.line_total is None else float(i.line_total),
                         None if o.order_total is None else float(o.order_total), i.category,
                         None if i.allocated_total is None else float(i.allocated_total)])
    _sheet(ws, ITEM_COLUMNS, rows, {6, 7, 8, 10}, {1: 12, 2: 12, 3: 22, 4: 60, 5: 6, 9: 20})
    for row in ws.iter_rows(min_row=2, min_col=1, max_col=1):
        row[0].number_format = "yyyy-mm-dd"

    wo = wb.create_sheet("Orders")
    order_rows = []
    for o in orders:
        items = float(o.items_sum)
        total = None if o.order_total is None else float(o.order_total)
        order_rows.append([o.date, o.retailer, o.order_number, sum(1 for i in o.items if not i.is_adjustment),
                           items, total, None if total is None else round(total - items, 2), o.url])
    _sheet(wo, ["Date", "Retailer", "Order Number", "Lines Read", "Items Sum", "Order Total",
                "Difference (tax/fees/missed)", "Link"], order_rows, {5, 6, 7}, {1: 12, 3: 22, 7: 16, 8: 50})
    for row in wo.iter_rows(min_row=2, min_col=1, max_col=1):
        row[0].number_format = "yyyy-mm-dd"

    wsum = wb.create_sheet("Weekly Summary")
    cols = weekly.columns()
    money = {n + 1 for n, c in enumerate(cols) if c not in ("Week Start", "Week End", "Full Week Covered",
                                                             "Grocery % of Budget", "Over Budget")}
    wrows = [[float(r[c]) if isinstance(r[c], Decimal) else r[c] for c in cols] for r in weekly_rows]
    _sheet(wsum, cols, wrows, money, {1: 12, 2: 12})
    wb.save(path)
