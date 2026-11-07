# Claude Duet onboarding: AI automation for small business

A turnkey class that takes a small-business owner from zero to running Claude as a personal assistant in one week: **one 4-hour Launch Day, then 30 minutes a day, one task a day, for 7 days.** It runs on the client's own Claude plan, sized to fit one week of Claude Code usage, and costs the operator about 5 hours per client.

The client leaves with:
- **Claude Duet** connected to their email and calendar with approvals on (or a fallback if they are still waitlisted).
- **A Claude Code workspace** that knows their business, writes in their voice, and has a slash command for each of their top time sinks.
- **A local sanitization check** they run before any folder or export reaches Claude.
- **A routine:** `/today` every morning, `/weekly-review` on Fridays, the sanitization check monthly.

## How a client goes through it

```
 intake sheet ──> build_kit.py ──> kit folder ──> Launch Day (4 h, live) ──> Days 1 to 7 (30 min, solo) ──> routine
  (20 min,         (5 min,          (zip it)       install, sanitize,         one task a day,              /today daily
   client)          operator)                      3 walkthroughs, Duet        5-min async check-in         /weekly-review
```

1. **Intake.** Send `intake/intake-sheet.md`. The client fills it in (about 20 minutes). It never asks for passwords, account numbers or customer records.
2. **Build the kit.** Copy the answers into a JSON file shaped like `intake/intake.example.json` (keep client files in `intake/clients/`, which git ignores), then:
   ```
   python3 onboarding/build_kit.py onboarding/intake/clients/<client>.json --check   # validate, show the week
   python3 onboarding/build_kit.py onboarding/intake/clients/<client>.json           # write onboarding/kits/<slug>/
   ```
   Every problem in the intake is listed at once. Kits land in `onboarding/kits/`, which git ignores.
3. **Launch Day.** Follow `curriculum/launch-day.md` minute by minute.
4. **Days 1 to 7.** The client follows their `WEEK-PLAN.md`. You send the check-in messages from `curriculum/daily-sessions.md`.

## The week

| | Length | What happens |
|---|---|---|
| **Launch Day** | 4 h, live | Install, sanitization check, business profile, morning brief, their #1 time sink done for real, Duet setup, usage habits |
| Day 1 | 30 min | Morning brief: run it alone, correct it, save a lesson |
| Days 2 to 5 | 30 min each | Their four top-ranked time sinks, one per day |
| Day 6 | 30 min | Build their own command from the job they described on the intake |
| Day 7 | 30 min | Weekly review, re-run the sanitization check, put the routine on the calendar |

Ten time sinks are pre-scripted in `library/`: email replies, quotes and proposals, invoice follow-ups, scheduling, social posts, review responses, meeting notes, bookkeeping summaries, written procedures, and hiring. Each one has the slash command, the 20-minute task with the exact words to type, the Duet handoff, and a Done-when checklist. `build_kit.py` fills in the client's business, voice, tools and rules.

## Fitting one week of Claude Code usage

The week is 13 "active blocks" of about 30 minutes of Claude work: 6 on Launch Day, 1 on each of Days 1 to 7.

| Client's plan | What the kit does |
|---|---|
| **Pro or Max** (needed for Duet) | Sonnet by default, one task per session with `/clear` between, daily `/usage` check at wrap-up. Launch Day is the heaviest day; the run sheet says what to do if a limit hits. |
| **API credits** | `budget.md` prices the week: about $12 on Sonnet 5.5 ($19 recommended with headroom), about $20 on Opus 5.5. The kit warns if the client's budget is below the recommendation. |

The per-block estimate assumes 1.5M cached tokens, 150K fresh input and 25K output, at Anthropic's published API rates as of November 2026. Measure a real client's week with `/cost` and adjust `BLOCK_TOKENS` in `build_kit.py` if your clients run heavier or lighter.

## The sanitization check

`sanitize_check.py` runs on the client's machine before Claude sees a folder. It is standard-library Python and nothing leaves the machine.

```
py tools/sanitize_check.py <folder> [--report notes/sanitize-report.md] [--deny-settings .] [--strict]
```

| Verdict | Meaning | What the client does |
|---|---|---|
| **BLOCK** | API keys, private keys, tokens, passwords, SSNs, Luhn-valid card numbers, bank routing and account numbers, `.env` files, key and password-vault files | Move it out of the workspace. Rotate anything that was ever shared. |
| **REVIEW** | Contact lists (3+ distinct emails or phones), dates of birth, EINs, private IP addresses, tax, payroll, ID or health documents by name | Decide once: keep, trim, or move. |
| **SKIPPED** | PDFs, images, archives, legacy Office files, oversized files | Nobody read it. Check by hand or keep it out. |
| **CLEAN** | No rule fired | Clean means "no rule fired", not "safe". |

It reads plain text and the text inside `.docx`, `.xlsx` and `.pptx`. It builds on the repo's pre-commit scanner (`git-tools/secret_scan.py`), so every key shape that scanner knows is covered too. It never prints what it found, only the rule, the line and the length. `--deny-settings` adds Claude Code `permissions.deny` rules for every BLOCK file as a backstop. The real fix is moving the file out: a deny rule on Read does not stop every possible way of opening a file.

The method on Launch Day is **copy in, do not point at**: check the client's folders, then copy the few files Claude needs into the workspace. Claude works on copies, never on live folders.

## Files

```
onboarding/
  README.md                  this page
  intake/
    intake-sheet.md          the client's intake form (each question names the JSON field it fills)
    intake.example.json      a complete fictional intake (Ridgeline Mobile Detailing)
  curriculum/
    launch-day.md            the operator's 4-hour run sheet, with troubleshooting
    daily-sessions.md        Days 1 to 7: format, check-in messages, recording once, operator time
  library/                   13 scripts: 10 time sinks plus the brief, build-your-own and weekly review
  build_kit.py               intake.json -> the client's workspace
  sanitize_check.py          the local sanitization check (copied into every kit's tools/)
  test_build_kit.py          library, validation, week plan, budget math, full build, overwrite guard
  test_sanitize_check.py     every rule both ways, Office files, verdicts, exit codes, deny-rule merge
```

Tests: `python3 -m unittest discover -s onboarding -p "test_*.py"`

## Notes and limits

- **Claude Duet** is a research preview (launched October 2026, Pro and Max subscribers, waitlisted). The Launch Day block is written so a waitlisted client loses nothing: the Claude Code commands cover the same jobs from files. Check Duet's menus and its usage accounting against the live product before each cohort; preview features change.
- **Install commands** in the run sheet are the official native installers at the time of writing. Check the Claude Code docs before each cohort.
- **The checker is a seatbelt, not an audit.** It does not read PDFs or images, and its PII rules are US-centric (SSN, ABA routing, EIN). Add rules in `sanitize_check.py` for other countries.
