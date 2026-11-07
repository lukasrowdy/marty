# Days 1 to 7: the daily sessions

After Launch Day the client works alone, 30 minutes a day, one task a day. Their scripts are already written for them in their kit's `WEEK-PLAN.md`, filled in with their business, their voice and their tools. Your job is a 5-minute async check-in each day.

## The shape of every day (30 minutes)

| Minutes | What | Why |
|---|---|---|
| 0 to 5 | `/today` | The habit. Every day starts with the brief. |
| 5 to 25 | The day's one task | One skill, practiced on real work. |
| 25 to 30 | Wrap-up: one line in `notes/daily-log.md`, check usage, `/clear` | Minutes saved get counted; usage never surprises. |

One task per day on purpose: it keeps each day inside 30 minutes, inside one Claude session, and inside the plan's usage limits.

## The week

| Day | Task | Source |
|---|---|---|
| 1 | Morning brief: run it alone, correct it, save a lesson | `library/daily-brief.md` |
| 2 | Time sink #1, solo (they did it with you on Launch Day) | their top-ranked key |
| 3 | Time sink #2 | intake rank 2 |
| 4 | Time sink #3 | intake rank 3 |
| 5 | Time sink #4 | intake rank 4 |
| 6 | Build your own command from their "dream automation" answer | `library/build-your-own.md` |
| 7 | Weekly review, re-run the sanitization check, set the routine | `library/graduation.md` |

If they ranked fewer than four time sinks, `build_kit.py` fills the gaps with email replies, meeting notes, quotes and procedures, in that order. Their 5th-ranked time sink (and any below it) is installed as an extra command for after the week.

## Recording once ("one take")

Every day's task is written so it also works as a video script: Why, then the numbered steps, then Done when. Record each day once, 5 to 8 minutes, with the example business from `intake/intake.example.json`, and send the same video to every client. The client's own `WEEK-PLAN.md` carries their personal version of the same steps, so the generic video never needs re-recording.

## Check-in messages (copy, paste, send at their daily slot)

Keep them short. Ask for the Done-when boxes, not a report.

- **Day 1:** "Morning! Day 1 is your brief: `/today`, correct one thing, save it to lessons. Reply with a thumbs up when the two boxes are ticked, or tell me what got in the way."
- **Day 2:** "Day 2: the job we did together Saturday, solo this time. How many of the drafts needed no edits?"
- **Day 3:** "Day 3 is in WEEK-PLAN.md. The first ten minutes build something you keep (a template or rules file); the rest uses it. Send me the one rule you added to lessons."
- **Day 4:** "Day 4. Halfway. Anything Claude keeps getting wrong? Tell it why, and say 'add that to lessons'. Then tell me, so I can improve the course."
- **Day 5:** "Day 5. Quick check: what does `/usage` (or `/cost`) say? If it is above what budget.md expects, reply and we will adjust."
- **Day 6:** "Day 6 is the fun one: you build your own command from the job you described on your intake sheet. If it needs your email or calendar directly, build the copy-paste version today and we will talk connections tomorrow."
- **Day 7:** "Last day. Run `/weekly-review`, re-run the sanitization check, and put the routine on your calendar. Want a 15-minute call to connect Duet or plan the next job? Reply with a time."

## When a client falls behind

- **Missed a day:** do not double up. Do the missed day's task, skip the next day's optional steps. Every day's task stands alone.
- **Hit a usage limit:** the work is saved in `outbox/`. Resume after the reset. If it happens twice, look at their session habits before suggesting a bigger plan: the usual cause is one very long session instead of `/clear` between tasks.
- **Claude did something they did not like:** ask for the file name and the words they used. Nearly always the fix is one line in `notes/lessons.md` or in the command file.

## Your time per client

| | Operator time |
|---|---|
| Review intake, build the kit, prep | 20 min |
| Launch Day | 4 h |
| Daily check-ins, 5 min x 7 | 35 min |
| **Total** | **about 5 h** |
