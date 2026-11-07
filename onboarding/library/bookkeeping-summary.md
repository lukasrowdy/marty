---
key: bookkeeping-summary
title: Making sense of your numbers
command: numbers
model: sonnet
---
## Why it matters
Your accounting software has the numbers; what you need is the story: what came in, what went out, what changed, and what to look at. Claude reads an export and tells you in plain words. It does not replace your bookkeeper and does not do taxes.

## Command
Summarize the numbers for {{business.name}}. Input (a CSV or spreadsheet export from {{tools.accounting}} in `inbox/`): $ARGUMENTS

1. First describe the file: columns, date range, row count. If it has account numbers, card numbers or employee pay, stop and say so: {{owner.first_name}} should remove them and re-export.
2. Compute, and show your working as a small table each time:
   - total in, total out, net, for the period
   - top 5 expense categories and top 5 customers or income sources
   - anything that changed more than 25% against the previous period, if the data has one
   - anything that looks unusual (a duplicate charge, a vendor seen once with a large amount)
3. Write `outbox/numbers-<period>.md`: five plain-language bullets {{owner.first_name}} would tell a business partner, then the tables, then "Questions for your bookkeeper".
4. Never give tax or legal advice. Say "ask your bookkeeper" instead. Every figure must come from the file; recheck totals before writing.

## Day task
**Goal: last month in five sentences.**

1. (4 min) Export last month's transactions or profit and loss from {{tools.accounting}} as CSV into `inbox/`.
2. (3 min) Run the sanitization check on `inbox/` before Claude reads it:
   > {{kit.python}} tools/sanitize_check.py inbox
3. (8 min) Run:
   > /numbers inbox/<your export>.csv
4. (5 min) Check two figures against your accounting app yourself. If they match, you can trust the method; if not, tell Claude what is off.

## With Claude Duet
Keep this one in Claude Code for now: it works on files you choose and checked, and nothing is connected to your accounts.

## Done when
- [ ] The export passed the sanitization check
- [ ] `outbox/numbers-<period>.md` with five bullets and tables
- [ ] Two figures spot-checked by you
