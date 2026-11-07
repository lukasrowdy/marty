---
key: daily-brief
title: Your morning brief
command: today
model: sonnet
---
## Why it matters
A good assistant starts the day by telling you what matters. This is the habit everything else hangs on: one command, every morning, five minutes.

## Command
You are {{owner.first_name}}'s assistant for {{business.name}}. Build today's brief.

1. Read `notes/daily-log.md` (the last 3 entries), `notes/lessons.md`, and anything new in `inbox/` (files changed since yesterday).
2. Write the brief to `outbox/brief-<today's date>.md` with these sections, each 5 lines or fewer:
   - **Top 3 today**: the three things that move the business today, most important first.
   - **Waiting on {{owner.first_name}}**: decisions or approvals only {{owner.first_name}} can make.
   - **Drafts ready**: anything in `outbox/` not yet marked SENT or DONE.
   - **Heads up**: deadlines in the next 3 days, anything that looks late.
3. Then show the brief here in chat, and ask one question: "Which of the top 3 do you want me to start on?"

Rules: only use what is in the files. If something is unclear, list it under Waiting on {{owner.first_name}} instead of guessing. Extra request for today: $ARGUMENTS

## Day task
**Goal: run your morning brief yourself, then make it yours.**

1. (2 min) Drop anything from yesterday into `inbox/`: a photo of your to-do list typed out, a few emails copied into a text file, a note to yourself. Messy is fine.
2. (3 min) Open Claude Code in your workspace and type `/today`.
3. (5 min) Read the brief. Is the Top 3 right? If not, tell Claude why, in plain words:
   > The top item should have been the Johnson fleet quote, because fleet jobs are worth 5x a single car. Remember that fleet work comes first.
4. (5 min) Ask Claude to save that preference:
   > Add that rule to notes/lessons.md so tomorrow's brief gets it right.
5. (5 min) Run `/today` again. Notice the difference. That loop (correct it once, write it down, never correct it again) is the whole method.

## With Claude Duet
If you have Duet, it can send you a morning summary from your connected email and calendar. Keep `/today` anyway for the first week: it covers the files on your computer, and comparing the two shows you what each one sees. Tell Duet the same priorities you put in `notes/lessons.md`.

## Done when
- [ ] `/today` ran and wrote a brief into `outbox/`
- [ ] You corrected it at least once and the correction is in `notes/lessons.md`
