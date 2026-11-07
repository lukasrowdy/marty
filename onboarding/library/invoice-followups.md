---
key: invoice-followups
title: Chasing unpaid invoices, politely
command: chase
model: sonnet
---
## Why it matters
Most late payments are forgotten, not refused. A friendly reminder on day 3, a firmer one on day 14 and a clear one on day 30 collects most of them, and nobody enjoys writing those emails. Claude does the writing; you stay in charge of the tone and the money.

## Command
Prepare payment reminders for {{business.name}}. Input (an export or a pasted list of open invoices): $ARGUMENTS

1. The list may come from {{tools.accounting}}. Read only what is needed: customer first name, invoice number, amount, due date. Ignore and never repeat bank or card details.
2. Sort into stages by days overdue: 1 to 7 friendly, 8 to 29 firm, 30 or more final. Show a table first: customer, invoice, amount, days late, stage.
3. Draft one email per invoice in `outbox/chase-<date>/`, in {{owner.first_name}}'s voice ({{voice.adjectives}}, signed "{{voice.sign_off}}"):
   - friendly: assume it slipped through; include amount, invoice number and how to pay [CHECK: payment link].
   - firm: state the date it was due and ask for a payment date.
   - final: say what happens next only if `reference/` has a late policy. Otherwise [CHECK: next step].
4. Never threaten, never add fees that are not in `reference/`, never send.

## Day task
**Goal: one pass over everything owed to you, with drafts ready to send.**

1. (5 min) Export open invoices from {{tools.accounting}} as CSV, or type a short list into `inbox/open-invoices.csv` (customer, invoice #, amount, due date). Remove account numbers.
2. (2 min) Run the sanitization check on `inbox/` (see the Launch Day notes) if the export came straight from accounting.
3. (8 min) Run:
   > /chase inbox/open-invoices.csv
4. (5 min) Read the table. Are the stages right? Is there a customer you handle differently (a regular who always pays late)? Tell Claude, and save it:
   > Mike at Peak Builders always pays at 45 days. Never go past friendly with him. Add to notes/lessons.md.

## With Claude Duet
Duet asks before any payment and any message, which is the right setting for money. You can ask it to remind you each week to run `/chase`, or to flag when a customer replies to a reminder.

## Done when
- [ ] A table of every open invoice by stage
- [ ] One draft per invoice in `outbox/chase-<date>/`
- [ ] Customer exceptions written into `notes/lessons.md`
