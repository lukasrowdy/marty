"""Retail order exporter: Amazon, Walmart and Sam's Club order history to CSV, Excel and a Ledger import file.

Everything runs locally. The browser is opened for you to log in by hand; no password is ever read,
typed or stored by this code, and the browser profile is thrown away when the run ends.
"""

CATEGORIES = ("Grocery", "Household", "Business/Materials", "Other")
RETAILERS = {"amazon": "Amazon", "walmart": "Walmart", "samsclub": "Sam's Club"}


def canonical_retailer(name: str) -> str:
    """'samsclub', "Sam's Club", 'SAMS CLUB' -> "Sam's Club"."""
    key = str(name).lower().replace("'", "").replace(" ", "").replace("’", "")
    if key not in RETAILERS:
        raise ValueError(f"unknown retailer {name!r}; expected one of {list(RETAILERS.values())}")
    return RETAILERS[key]
