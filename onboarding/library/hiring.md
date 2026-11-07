---
key: hiring
title: Job posts and applicant screening
command: hire
model: sonnet
---
## Why it matters
Hiring takes time you do not have, exactly when you are busiest. Claude writes a clear post and turns a pile of applications into a short, fair comparison against the criteria you choose. You make every decision.

## Command
Help {{owner.first_name}} hire for {{business.name}}. Request: $ARGUMENTS

1. **Job post**: ask for role, pay range, hours and the 3 must-haves if not given. Write a post that says what the job really is, the pay, the schedule, and how to apply. Voice: {{voice.adjectives}}. No inflated language.
2. **Screening**: for applications in `inbox/applicants/`, compare each one only against the written must-haves and nice-to-haves. Output a table: applicant (first name and initial), must-haves met (yes/no each), nice-to-haves, questions to ask. No overall ranking score.
3. Fairness rules: never consider or mention age, gender, race, religion, national origin, disability, pregnancy, marital status, or anything not job-related. Do not guess at any of these from names, photos, dates or gaps. Remove such details from your summary.
4. Save to `outbox/hiring-<role>-<date>.md`. {{owner.first_name}} decides who to call. Never contact applicants.

## Day task
**Goal: a job post ready to publish, and a screening checklist you trust.**

1. (8 min) Run:
   > /hire write a job post for <the role you need or will need next>
2. (6 min) Ask Claude to turn your must-haves into a 5-question phone screen:
   > Now write a 10-minute phone screen with 5 questions that test the must-haves, and what a good answer sounds like.
3. (6 min) Save both into `templates/`. If you have real applications, put them in `inbox/applicants/` after running the sanitization check on that folder, then try the screening step.

## With Claude Duet
Duet can flag incoming applications by email and keep them together. Keep the decisions and all replies with you.

## Done when
- [ ] Job post and phone screen in `templates/`
