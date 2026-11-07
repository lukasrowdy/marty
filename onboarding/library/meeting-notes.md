---
key: meeting-notes
title: Call and meeting notes to action items
command: notes
model: sonnet
---
## Why it matters
The value of a call is in the follow-up, and the follow-up is what gets dropped. Talk or type messy notes; Claude turns them into decisions, action items and the follow-up email.

## Command
Turn these notes into something {{owner.first_name}} can act on. Notes (pasted, a file in `inbox/`, or a transcript): $ARGUMENTS

1. Write to `outbox/notes-<who>-<date>.md`:
   - **Summary**: three lines.
   - **Decisions**: what was agreed.
   - **Action items**: who, what, by when. Mark anything with no owner or no date as [CHECK].
   - **Numbers mentioned**: prices, quantities, dates, so nothing is lost.
2. Draft the follow-up email to the other person in {{owner.first_name}}'s voice ({{voice.adjectives}}, signed "{{voice.sign_off}}"): thank them, restate decisions and next steps, nothing that was not agreed.
3. Add {{owner.first_name}}'s own action items to the bottom of `notes/daily-log.md` under today's date, so tomorrow's `/today` sees them.

## Day task
**Goal: one real conversation turned into actions and a follow-up in 10 minutes.**

1. (5 min) Pick a recent call or meeting. Type or dictate everything you remember into `inbox/call-notes.txt`. Do not tidy it. (On Windows, Win+H starts dictation; on a Mac, press the microphone key or Fn twice.)
2. (5 min) Run:
   > /notes inbox/call-notes.txt
3. (5 min) Check the action items. Did it catch everything? Correct it.
4. (5 min) Run `/today` and confirm your action items show up in the brief.

## With Claude Duet
Duet can watch for the follow-up you promised and nudge you if it has not gone out. Tell it the follow-up rule you want ("same day for quotes, within 48 hours for everything else").

## Done when
- [ ] Notes file and follow-up draft in `outbox/`
- [ ] Your action items added to `notes/daily-log.md`
