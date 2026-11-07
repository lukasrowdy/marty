# Order exporter

Pulls your order history from **Amazon, Walmart and Sam's Club** into:

1. one combined **CSV** and an **Excel** workbook with every line item,
2. a **category tag** on every item (Grocery, Household, Business/Materials, Other) from rules you edit,
3. a **Ledger import CSV**,
4. a **weekly summary CSV** with fixed columns, ready to paste into the same Google Sheet every week.

You log in yourself, in a normal browser window. The script never sees, types or stores a password. Everything runs and stays on your PC: no cloud services, no accounts, no API keys.

**Status:** built and tested against the sample file and against local test pages shaped like each retailer's order pages. **It has not yet been run against the live Amazon, Walmart or Sam's Club sites.** Those sites change their pages often, so expect the first real run to need a small fix in `sites.toml` for one of them. See [When a site changes](#when-a-site-changes).

---

## Windows: step by step

### One-time setup

1. **Install Python 3.11 or newer** from <https://www.python.org/downloads/>. On the first installer screen, tick **"Add python.exe to PATH"**, then click Install Now.
2. **Get this folder onto your PC.** Either clone the repo, or on GitHub click **Code > Download ZIP**, unzip it, and open the `order-exporter` folder.
3. **Double-click `setup.bat`.** It makes a private Python environment in `.venv` inside this folder and installs the two packages (Playwright and openpyxl). Takes a minute or two. It ends with "Setup finished".

The exporter drives **Google Chrome**. If Chrome isn't installed it uses **Microsoft Edge** instead, which every Windows 11 PC already has, so there's nothing else to install.

### Test it without logging in (dry run)

4. **Double-click `dry-run.bat`.** It reads `sample\sample_orders.json` (made-up orders), runs the whole pipeline, and writes every output file to `output\dry-run\`. No browser opens. Nothing is remembered, so a dry run never affects a real run.
5. Open `output\dry-run\` and look at the files. If they look right, you're ready.

From a Command Prompt instead of double-clicking:

```
cd C:\path\to\order-exporter
run.bat --dry-run
```

### The real run

6. **Set your weekly grocery budget** and anything else in `config.toml` (open it with Notepad). See [Settings](#settings).
7. **Double-click `run.bat`** (or run `run.bat` from a Command Prompt). By default it reads the last 30 days.
8. **Pick your vendors.** The console asks:
   ```
   Which vendors should I export?
       1) Amazon
       2) Walmart
       3) Sam's Club
     Type numbers or names separated by commas (like 1,3), or all.
     Press Enter for: Amazon, Walmart, Sam's Club
   ```
   Type `1,3`, `amazon, sams`, or `all`, or just press Enter for the vendors listed in `config.toml`.
9. **Log in once, on every tab.** Chrome opens with one tab per vendor you picked, each on its sign-in page. Log in on each tab yourself (and pass any "are you a robot" check). When you're logged in on all of them, **switch back to the black console window and press Enter once.**
10. The script checks every tab. If one still shows a sign-in page or a robot check, it names that vendor and waits for you to finish there and press Enter again.
11. Then it exports each vendor in turn, page by page, with no more questions. Leave the browser alone while it works. If a site asks you to log in again or shows a robot check partway through, the console tells you; deal with it in the browser and press Enter.
12. When it finishes, the browser closes and the console lists the files it wrote in `output\`. Press any key to close the console.

You log in again on each run: the browser is temporary and keeps nothing once it closes (see [Privacy and safety](#privacy-and-safety)). To skip the vendor question, set `ask_for_vendors = false` in `config.toml`, or name the vendors on the command line with `--retailers`.

Stop any time with **Ctrl+C**; orders already read are kept and written out.

### The weekly routine

Every week (say Monday morning), from a Command Prompt in this folder:

```
run.bat --last-week
```

That reads only the previous full week (Monday to Sunday by default), and gives you a one-row weekly summary to paste into your Google Sheet and a Ledger file with that week's lines.

### All the options

```
run.bat                              asks which vendors, then reads the last 30 days (lookback_days in config.toml)
run.bat --last-week                  the previous full week
run.bat --week 2026-10-28            the full week containing that date
run.bat --since 2026-01-01           from a date to today
run.bat --since 2026-01-01 --until 2026-03-31
run.bat --retailers amazon,walmart   these vendors, without asking (amazon, walmart, samsclub)
run.bat --dry-run                    sample file, no browser, nothing remembered
run.bat --from-json output\raw_orders_2026-10-08_to_2026-11-07.json
                                     re-tag a saved scrape with your updated rules, no login needed
run.bat --ledger-all                 put every line in the Ledger file, even ones exported before
run.bat --debug                      save a copy of every order page to debug\ (for fixing sites.toml)
```

---

## What you get

Every run writes into `output\` (dry runs into `output\dry-run\`). File names carry the date range, for example `orders_2026-10-27_to_2026-11-02.csv`.

| File | What it is |
|---|---|
| `orders_<range>.csv` | Every line item from all three retailers. Opens straight in Excel. |
| `orders_<range>.xlsx` | The same in Excel, with three sheets: **Line Items**, **Orders** (one row per order, with a Difference column that shows tax/fees, or an item the scraper missed), and **Weekly Summary**. |
| `ledger_import_<date>_<time>.csv` | The file to import into Ledger. Named for when it was made, so a later run never overwrites one you haven't imported yet. |
| `weekly_summary_<range>.csv` | One row per week, fixed columns. |
| `raw_orders_<range>.json` | Exactly what was read from the sites. Lets you re-run with `--from-json` after changing rules, without logging in again. |

### Line items (CSV and the Line Items sheet)

| Column | Meaning |
|---|---|
| Date | Order date, YYYY-MM-DD |
| Retailer | Amazon, Walmart or Sam's Club |
| Order Number | The retailer's order number |
| Item | Item name as the site shows it |
| Qty | Quantity |
| Unit Price | Price of one |
| Line Total | Qty x Unit Price |
| Order Total | What the whole order cost (tax, shipping and fees included). **Repeated on every line of the order, so don't sum this column.** |
| Category | Grocery, Household, Business/Materials or Other |
| Amount Incl Tax/Fees | Line Total plus this line's share of the order's tax, shipping, fees and discounts. These add up to the Order Total. |

**How tax and fees are shared out** (`order_adjustments = "allocate"`, the default): an order's tax, shipping, fees and discounts are spread across its items in proportion to price, so groceries carry their own tax and the lines of an order add up exactly to what hit your card. If the items and the order total are more than 25% apart (`max_adjustment_percent`), that usually means an item wasn't read, so the gap is **not** spread; it goes on its own line called "Order adjustment (tax, fees, discounts or items not read)", tagged Other, and the console lists it under "things to check". Set `order_adjustments = "ignore"` to use plain item prices instead.

---

## Category rules

Tags come from `category_rules.csv`. Edit it in Excel or Notepad. Columns:

| Column | Meaning |
|---|---|
| category | `Grocery`, `Household`, `Business/Materials` or `Other` |
| match | `word` (the default), `contains`, or `regex` |
| pattern | What to look for in the item name. Case doesn't matter. |
| retailer | Optional. `Amazon`, `Walmart` or `Sam's Club`; blank means any |
| note | Optional, for you |

- Rules are checked **top to bottom, and the first match wins.** Put specific rules above general ones. For example, "nail polish" (Household) sits above "nail" (Business/Materials).
- `word` matches whole words and their plural: `egg` matches "Eggs, 18 ct" but not "Eggplant".
- `contains` matches anywhere, even inside a word.
- `regex` is a Python regular expression, for the rare case that needs one.
- Anything no rule matches is tagged **Other**. Rows whose category starts with `#` are comments.
- A typo in a category name stops the run with the line number, before any login.

After changing rules, re-tag your last scrape without logging in:

```
run.bat --from-json output\raw_orders_<range>.json
```

---

## Ledger import file

No Ledger importer code exists in this repo, so the file uses this format. If your Ledger app expects something different, the date format, description, account and category names are all settings in `config.toml`, under `[ledger]`.

```
date,description,amount,account,category
2026-10-19,Amazon: HP 67XL Black High-yield Ink Cartridge,-37.42,Credit Card,Business/Materials
2026-10-20,"Walmart: Great Value Large White Eggs, 18 Count",-4.20,Credit Card,Grocery
```

| Column | Format |
|---|---|
| date | Order date. `2026-10-19` by default (`date_format`; `"%m/%d/%Y"` gives `10/19/2026`). |
| description | `Retailer: Item name` by default (`description`; placeholders `{retailer}` `{item}` `{order}` `{qty}` `{category}`). |
| amount | **Negative for spending**, two decimals, no `$` and no thousands separator: `-37.42`. It's the Amount Incl Tax/Fees, so an order's lines add up to the card charge. |
| account | The account each retailer is paid from (`[ledger.accounts]`), `Credit Card` by default. |
| category | The item's tag, renamed to your Ledger names if you set `[ledger.category_names]` (for example `"Grocery" = "Groceries"`). |

The file is a standard comma-separated CSV: UTF-8, a header row, and fields with commas wrapped in double quotes. It has no byte-order mark unless you set `utf8_bom = true`.

**No double imports.** The exporter remembers which lines it has already put into a Ledger file (in `state\ledger_exported.txt`) and leaves them out next time, so overlapping runs never import a purchase twice. If there's nothing new, no Ledger file is written. To include everything for one run, add `--ledger-all`. To forget the history, delete `state\ledger_exported.txt`. Dry runs never read or change it.

---

## Weekly summary and Google Sheets

`weekly_summary_<range>.csv` has **one row per week and always the same 28 columns in the same order**, even when a retailer had no orders that week, so it pastes into the same place in your sheet every time:

```
Week Start, Week End, Full Week Covered,
Amazon Grocery, Amazon Household, Amazon Business/Materials, Amazon Other, Amazon Total,
Walmart Grocery, Walmart Household, Walmart Business/Materials, Walmart Other, Walmart Total,
Sam's Club Grocery, Sam's Club Household, Sam's Club Business/Materials, Sam's Club Other, Sam's Club Total,
Total Grocery, Total Household, Total Business/Materials, Total Other, Total Spend,
Grocery Budget, Grocery Spent, Grocery Remaining, Grocery % of Budget, Over Budget
```

- Amounts include each item's share of tax and fees, so Total Spend matches what was charged.
- **Grocery Budget** is `weekly_grocery` from `config.toml`. Grocery Remaining goes negative when you're over; Over Budget says Yes or No.
- **Full Week Covered** is No when the run didn't cover that whole week (a partial first or last week), so a low number there isn't mistaken for a cheap week.
- A retailer you didn't include in the run shows zeros.

**Pasting into Google Sheets each week:**

1. Make the header row in your sheet once: open the CSV in Excel or Notepad, copy the first line, and paste it into row 1 of your sheet. (In Sheets, use **Data > Split text to columns** if it lands in one cell.)
2. Each week, after `run.bat --last-week`, open the new `weekly_summary_...csv` in Excel, copy the data row (row 2), and paste it into the next empty row of your sheet.

---

## Settings

All in `config.toml` (open with Notepad). The main ones:

| Setting | Default | Meaning |
|---|---|---|
| `retailers` | all three | The vendors a run reads; the default answer to the vendor question |
| `ask_for_vendors` | `true` | Ask which vendors to export at the start of each run |
| `lookback_days` | 30 | How far back a run with no dates goes |
| `week_starts_on` | `"monday"` | First day of the week for summaries and `--last-week` |
| `output_dir` | `"output"` | Where files go |
| `order_adjustments` | `"allocate"` | Share tax/fees across items, or `"ignore"` |
| `weekly_grocery` | 250.00 | Weekly grocery budget |
| `channel` | `"chrome"` | Browser: `chrome`, `msedge`, or `chromium` (needs `.venv\Scripts\python -m playwright install chromium`). If it won't start, the others are tried in turn. |
| `delay_seconds` | 2.0 | Pause between order pages. Slower is gentler and trips fewer robot checks. |
| `[ledger]` | | Ledger date format, description, accounts, category names, duplicate skipping |

`sites.toml` holds how each retailer's pages are read. You only touch it when a site changes.

---

## Privacy and safety

- **No passwords.** You log in by hand in the browser. The script has no login code, never types into a login form, and has nowhere to store credentials.
- **No saved session.** Each run uses a brand-new, temporary browser profile that's deleted when the browser closes. Cookies don't survive the run, which is why you log in each time.
- **Nothing leaves your PC.** The script only talks to the three retailer sites, through the browser you're watching. No analytics, no cloud, no third-party services.
- **Your data stays out of git.** `output\`, `state\` and `debug\` are in `.gitignore`.
- `debug\` snapshots (written when an order page can't be read, or with `--debug`) are copies of your order pages and can include your address and the last digits of your card. Delete them when you're done.

---

## When a site changes

Retailers redesign their order pages without warning. Signs: a retailer shows "no order links found", orders show "0 item(s)", or the console lists "no line items were read".

1. Run just that retailer with `--debug`, for example `run.bat --retailers walmart --since 2026-11-01 --debug`.
2. Open the files in `debug\`: the `.txt` file is the page's text, and the `.html` file is the page itself.
3. Adjust that retailer's section in `sites.toml`. Each setting is commented. The usual fixes:
   - **No orders found:** `order_link_regex` (the shape of links to an order's detail page), or `order_id_text_regex` with `order_url_template` (when the list shows order numbers but no links).
   - **Orders found, no items:** `product_link_regex` (the shape of product links on a detail page).
   - **Wrong date or total:** `date_patterns` and `total_patterns`.
   - **Prices doubled or divided by the quantity:** flip `price_is_line_total` for that retailer.
4. Check the fix against a known order: on the **Orders** sheet of the Excel file, the Difference column should only show tax and fees.

Patterns are Python regular expressions. In `sites.toml` they're written in single quotes, so backslashes need no escaping.

---

## Known limits

- **Not yet verified on the live sites** (see Status at the top). The first real run is the real test.
- **Returns and refunds** aren't subtracted. A returned item still shows as bought.
- **Cancelled orders** are skipped when the page says the whole order was cancelled. A single cancelled item in an otherwise delivered order may still show up.
- **Amazon Fresh and Whole Foods orders** use different pages on Amazon and may not be read.
- **Walmart and Sam's Club weighed items** (produce by the pound) are read as quantity 1 at the final price.
- **Multi-year ranges on Amazon** are read one year at a time; that's handled automatically.
- **Robot checks.** Walmart in particular may show a "press and hold" check. The script pauses for you to solve it. A larger `delay_seconds` makes checks less likely.

---

## For developers

```
order-exporter/
  export_orders.py      command line entry point
  exporter/
    models.py           Order, LineItem, money / quantity / date parsing
    config.py           reads config.toml and sites.toml
    rules.py            category rules
    process.py          date filtering, tagging, tax and fee allocation
    weekly.py           weekly summary rows (fixed columns)
    outputs.py          CSV, Excel and Ledger writers, the already-exported list
    scraper.py          the browser engine shared by all three retailers
  sites.toml            per-retailer URLs, link shapes and labels
  category_rules.csv    category rules
  config.toml           settings
  sample/sample_orders.json   made-up orders for --dry-run
  tests/                unit tests, plus browser tests against local mock pages in tests/fixtures
```

Run the tests (the browser tests skip themselves if no browser is available):

```
.venv\Scripts\python -m unittest discover -s tests -v
```

The browser tests serve the pages in `tests/fixtures` from a local web server and run the real scraper against them, headless. They check paging, stopping at the start date, item and quantity reading, unit vs line prices, strikethrough and per-pound prices, and skipping recommendation carousels. They show the engine works; they can't show the live sites still look like the fixtures.
