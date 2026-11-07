"""Reads config.toml (your settings) and sites.toml (how each retailer's pages are read)."""
from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from . import CATEGORIES, RETAILERS
from .models import DATE_RE

HERE = Path(__file__).resolve().parent.parent
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


@dataclass
class Config:
    retailers: list[str]
    ask_for_vendors: bool
    lookback_days: int
    week_starts_on: int  # 0 = Monday ... 6 = Sunday
    output_dir: Path
    order_adjustments: str  # "allocate" or "ignore"
    max_adjustment_percent: Decimal
    weekly_grocery_budget: Decimal
    browser_channel: str
    delay_seconds: float
    max_orders_per_retailer: int
    max_list_pages: int
    ledger_date_format: str
    ledger_description: str
    ledger_skip_already_exported: bool
    ledger_bom: bool
    ledger_accounts: dict[str, str] = field(default_factory=dict)
    ledger_category_names: dict[str, str] = field(default_factory=dict)
    rules_file: Path = HERE / "category_rules.csv"
    sites_file: Path = HERE / "sites.toml"
    state_dir: Path = HERE / "state"
    debug_dir: Path = HERE / "debug"


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else HERE / path


def load_config(path: Path | None = None) -> Config:
    path = path or HERE / "config.toml"
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    g = raw.get("general", {})
    b = raw.get("budget", {})
    br = raw.get("browser", {})
    lg = raw.get("ledger", {})

    retailers = [r.lower().replace("'", "").replace(" ", "") for r in g.get("retailers", list(RETAILERS))]
    unknown = [r for r in retailers if r not in RETAILERS]
    if unknown:
        raise ValueError(f"config.toml: unknown retailer(s) {unknown}; use {list(RETAILERS)}")

    week_day = str(g.get("week_starts_on", "monday")).lower()
    if week_day not in WEEKDAYS:
        raise ValueError(f"config.toml: week_starts_on must be one of {WEEKDAYS}")

    mode = str(g.get("order_adjustments", "allocate")).lower()
    if mode not in ("allocate", "ignore"):
        raise ValueError('config.toml: order_adjustments must be "allocate" or "ignore"')

    names = {c: c for c in CATEGORIES}
    names.update({k: str(v) for k, v in lg.get("category_names", {}).items() if k in CATEGORIES})
    accounts = {name: "Credit Card" for name in RETAILERS.values()}
    accounts.update({str(k): str(v) for k, v in lg.get("accounts", {}).items()})

    return Config(
        retailers=retailers,
        ask_for_vendors=bool(g.get("ask_for_vendors", True)),
        lookback_days=int(g.get("lookback_days", 30)),
        week_starts_on=WEEKDAYS.index(week_day),
        output_dir=_resolve(g.get("output_dir", "output")),
        order_adjustments=mode,
        max_adjustment_percent=Decimal(str(g.get("max_adjustment_percent", 25))),
        weekly_grocery_budget=Decimal(str(b.get("weekly_grocery", 0))).quantize(Decimal("0.01")),
        browser_channel=str(br.get("channel", "chrome")).lower(),
        delay_seconds=float(br.get("delay_seconds", 2.0)),
        max_orders_per_retailer=int(br.get("max_orders_per_retailer", 300)),
        max_list_pages=int(br.get("max_list_pages", 30)),
        ledger_date_format=str(lg.get("date_format", "%Y-%m-%d")),
        ledger_description=str(lg.get("description", "{retailer}: {item}")),
        ledger_skip_already_exported=bool(lg.get("skip_already_exported", True)),
        ledger_bom=bool(lg.get("utf8_bom", False)),
        ledger_accounts=accounts,
        ledger_category_names=names,
        rules_file=_resolve(g.get("rules_file", "category_rules.csv")),
        sites_file=_resolve(g.get("sites_file", "sites.toml")),
    )


def load_sites(path: Path) -> dict[str, dict]:
    """Each retailer's section merged over [defaults]. Lists in a retailer section replace the default list,
    except *_extra keys, which are appended to the matching default list."""
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    defaults = raw.get("defaults", {})
    sites = {}
    for key in RETAILERS:
        if key not in raw:
            continue
        site = copy.deepcopy(defaults)
        for k, v in raw[key].items():
            if k.endswith("_extra"):
                base = k[: -len("_extra")]
                site[base] = list(v) + list(site.get(base, []))
            else:
                site[k] = v
        site["key"] = key
        site.setdefault("name", RETAILERS[key])
        for k in ("date_patterns", "total_patterns"):
            site[k] = [p.replace("{date}", DATE_RE) for p in site.get(k, [])]
        sites[key] = site
    return sites
