---
key: graduation
title: Weekly review and your routine from here
command: weekly-review
model: sonnet
---
## Why it matters
The assistant gets better only when its mistakes are written down. Once a week, ten minutes: what worked, what to fix, what to hand off next. This is the habit that keeps the system improving after the course ends.

## Command
Run the weekly review for {{owner.first_name}} at {{business.name}}.

1. Read `notes/daily-log.md`, `notes/lessons.md`, the file names in `outbox/` from the last 7 days, and the list of commands in `.claude/commands/`.
2. Write `notes/weekly-review-<date>.md`:
   - **What got done**: count of drafts, quotes, replies and so on by type.
   - **Time saved, roughly**: use {{owner.first_name}}'s own estimates if they are in the log; otherwise ask.
   - **Lessons**: tidy `notes/lessons.md`: merge duplicates, remove contradictions (ask which one wins), keep it under 40 lines. Show the changes before saving.
   - **Rules to promote**: lessons that should move into CLAUDE.md because they apply to everything. Propose the exact lines; save only on a yes.
   - **Next job to hand off**: one suggestion, from what took the most time this week.
3. Remind {{owner.first_name}} to run the sanitization check on any new folder before sharing it.

Extra focus for this review: $ARGUMENTS

## Day task
**Goal: graduate with a routine that runs without help.**

1. (8 min) Run `/weekly-review`. Approve or reject each proposed change.
2. (4 min) Re-run the sanitization check on every folder you now share:
   > {{kit.python}} tools/sanitize_check.py inbox reference templates --report notes/sanitize-report.md
3. (4 min) Check your usage for the week (see `budget.md`) and note whether you would change plans.
4. (4 min) Put your routine on the calendar: `/today` every morning, `/weekly-review` every Friday, the sanitization check on the first of each month.

## With Claude Duet
Ask Duet to remind you about the Friday review. If you came off the waitlist this week, the operator check-in today is the time to connect it.

## Done when
- [ ] `notes/weekly-review-<date>.md` saved
- [ ] Sanitization report is clean, or every flagged file has a decision
- [ ] Routine is on your calendar
