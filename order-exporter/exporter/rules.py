"""Category tagging from category_rules.csv.

The rules file is a plain CSV you can edit in Excel or Notepad. Columns:

    category   one of Grocery, Household, Business/Materials, Other
    match      word (default), contains, or regex
    pattern    the text to look for in the item name (case does not matter)
    retailer   optional: Amazon, Walmart or Sam's Club; blank means any retailer
    note       optional, ignored

Rules are checked top to bottom and the FIRST match wins, so put specific rules above general ones.
An item no rule matches is tagged Other. Rows whose category starts with # are comments.

"word" matches whole words and also the plural: "egg" matches "Eggs, 12 ct" but not "Eggplant".
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from . import CATEGORIES

DEFAULT_CATEGORY = "Other"


@dataclass
class Rule:
    category: str
    regex: re.Pattern
    retailer: str  # "" for any
    line: int
    pattern: str


def _norm_retailer(s: str) -> str:
    return s.lower().replace("'", "").replace(" ", "")


def load_rules(path: Path) -> list[Rule]:
    rules: list[Rule] = []
    lookup = {c.lower(): c for c in CATEGORIES}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = {"category", "pattern"} - {(h or "").strip().lower() for h in (reader.fieldnames or [])}
        if missing:
            raise ValueError(f"{path.name}: missing column(s) {sorted(missing)}")
        for n, row in enumerate(reader, start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            cat = row.get("category", "")
            if not cat or cat.startswith("#"):
                continue
            if cat.lower() not in lookup:
                raise ValueError(f"{path.name} line {n}: category {cat!r} is not one of {list(CATEGORIES)}")
            pattern = row.get("pattern", "")
            if not pattern:
                continue
            kind = (row.get("match") or "word").lower()
            if kind == "word":
                rx = r"(?<![A-Za-z0-9])" + re.escape(pattern) + r"(?:s|es)?(?![A-Za-z0-9])"
            elif kind == "contains":
                rx = re.escape(pattern)
            elif kind == "regex":
                rx = pattern
            else:
                raise ValueError(f"{path.name} line {n}: match must be word, contains or regex, not {kind!r}")
            try:
                compiled = re.compile(rx, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"{path.name} line {n}: bad regex {pattern!r}: {e}") from e
            rules.append(Rule(lookup[cat.lower()], compiled, _norm_retailer(row.get("retailer", "")), n, pattern))
    return rules


def categorize(name: str, retailer: str, rules: list[Rule]) -> str:
    r = _norm_retailer(retailer)
    for rule in rules:
        if rule.retailer and rule.retailer != r:
            continue
        if rule.regex.search(name):
            return rule.category
    return DEFAULT_CATEGORY
