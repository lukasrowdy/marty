---
key: build-your-own
title: Build your own command
command: new-job
model: sonnet
---
## Why it matters
Every command you used this week is just a written-down job description. Today you write one yourself, for the job you most wanted to hand off when you filled in the intake sheet. After today you can keep adding them without anyone's help.

## Command
Help {{owner.first_name}} turn a recurring job into a new Claude Code command for {{business.name}}. The job: $ARGUMENTS

1. Interview {{owner.first_name}} (at most 6 questions, one at a time): what triggers it, what goes in, what comes out, where the output should be saved, what must never happen, and how to tell it was done well.
2. Show the proposed command in chat first. It must include: where to read facts from (`reference/`, `notes/lessons.md`), where to save output (`outbox/`), the voice rules from CLAUDE.md, a [CHECK] rule for missing facts, and "never send, pay, post or delete".
3. Only after {{owner.first_name}} says yes, save it as `.claude/commands/<short-name>.md` and explain how to run it.
4. Then run it once on a real or sample input so {{owner.first_name}} sees it work.

## Day task
**Goal: one new command that is yours.**

Suggested starting point from your intake sheet:
> {{dream_automation}}

1. (12 min) Run:
   > /new-job {{dream_automation}}
   and answer the questions.
2. (5 min) Approve the command and run it once.
3. (3 min) Fix one thing in it, and confirm the fix is saved in the command file.

If your idea needs something Claude Code cannot reach yet (your calendar or email directly), build the version that works from a file you paste into `inbox/`, and note the connection you would want for the review on Day 7.

## With Claude Duet
Recurring jobs that start from email or calendar events are a natural fit for Duet. Describe the job to Duet in the same words you used today.

## Done when
- [ ] A new `.claude/commands/<name>.md` you approved
- [ ] It ran once and produced output in `outbox/`
