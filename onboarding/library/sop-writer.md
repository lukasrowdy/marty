---
key: sop-writer
title: Writing down how things are done
command: sop
model: sonnet
---
## Why it matters
If a job lives only in your head, only you can do it. A written procedure lets you hand it to an employee, and it is also exactly what Claude needs to do the job with you.

## Command
Write a standard operating procedure for {{business.name}}. Process: $ARGUMENTS

1. Interview {{owner.first_name}} one question at a time (at most 8 questions): trigger, steps in order, tools, what good looks like, common mistakes, who to ask when stuck.
2. Write `reference/sop-<process>.md`:
   - Purpose (one line), When to use it, What you need
   - Steps: numbered, one action each, written so a new hire on day one could follow them
   - Checks: how to know it was done right
   - If something goes wrong: the 3 most likely problems and what to do
3. Plain words, no jargon. Mark anything uncertain [CHECK].
4. Finish by saying whether part of this process could become a Claude command, and which part.

## Day task
**Goal: one process out of your head and onto paper.**

1. (2 min) Pick the process you explain most often to helpers.
2. (12 min) Run:
   > /sop <that process>
   and answer the questions out loud or typed. Short answers are fine.
3. (6 min) Read it as if you were new. Fix what is unclear. Note Claude's suggestion for what could be automated: it may be your Day 6 project.

## With Claude Duet
Once a procedure is written, you can tell Duet to follow it when that situation comes up in your inbox or calendar.

## Done when
- [ ] `reference/sop-<process>.md` exists and a new hire could follow it
