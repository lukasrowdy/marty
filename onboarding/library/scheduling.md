---
key: scheduling
title: Scheduling, reminders and reschedules
command: schedule
model: sonnet
---
## Why it matters
Every booking is three or four messages: offer times, confirm, remind, reschedule. Claude can write all of them from your calendar and your rules about when you work.

## Command
Help {{owner.first_name}} with scheduling for {{business.name}}. Request: $ARGUMENTS

1. Working hours are {{business.hours}} ({{business.timezone}}). Read `reference/scheduling-rules.md` for buffers, travel time and days off. If it does not exist, ask {{owner.first_name}} the five questions needed to write it, then write it.
2. If {{owner.first_name}} pasted calendar entries or bookings, use only those. Never assume a slot is free that was not shown as free.
3. Produce what was asked:
   - **Offer times**: two or three specific options, earliest first.
   - **Confirmation**: date, time window, address or location, what the customer should prepare.
   - **Reminder**: one short message for the day before.
   - **Reschedule**: apologize once, offer two new options, no long explanation.
4. Save to `outbox/schedule-<date>.md`. Voice: {{voice.adjectives}}, signed "{{voice.sign_off}}". Never send, never edit the calendar.

## Day task
**Goal: tomorrow's reminders written in 5 minutes, and your scheduling rules on paper.**

1. (6 min) Let Claude interview you:
   > /schedule I have no scheduling rules written down yet. Interview me and write reference/scheduling-rules.md.
2. (4 min) Copy tomorrow's bookings from {{tools.calendar}} into `inbox/tomorrow.txt` (customer first name, time, place, job type).
3. (6 min) Run:
   > /schedule write a reminder for each booking in inbox/tomorrow.txt
4. (4 min) Fix one reminder and save the fix to `notes/lessons.md`.

## With Claude Duet
This is where Duet shines: it reads your calendar directly and can propose reminders and reschedules without copy and paste. Give it your `reference/scheduling-rules.md`, and keep "ask before sending" on.

## Done when
- [ ] `reference/scheduling-rules.md` exists
- [ ] Reminders for tomorrow in `outbox/`
