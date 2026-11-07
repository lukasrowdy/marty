---
key: social-posts
title: A week of social posts in one sitting
command: post
model: sonnet
---
## Why it matters
Posting regularly matters more than posting brilliantly. Batch a week of posts in one sitting, in your voice, from your real jobs, and the "what do I post today" problem disappears.

## Command
Write social posts for {{business.name}} ({{business.description}}). Topic or material: $ARGUMENTS

1. Platforms: {{tools.social}}. Write a version for each, sized for it (short for Google Business Profile, a little longer for Facebook, a caption plus hashtag line for Instagram).
2. Use only real facts: from `reference/`, from `inbox/` notes about recent jobs, or from what {{owner.first_name}} says here. No made-up reviews, numbers, awards or before-and-after claims.
3. Voice: {{voice.adjectives}}. Never use: {{voice.never_say}}. One clear call to action per post (book, call, reply).
4. Never name a customer or show an address unless {{owner.first_name}} confirms the customer agreed.
5. Save to `outbox/posts-<date>.md` with a suggested day for each. Never post anything.

## Day task
**Goal: five posts ready for the week.**

1. (5 min) Write five one-line notes in `inbox/post-ideas.txt`: a job you are proud of, a tip customers always ask about, a seasonal reminder, a team shout-out, an offer.
2. (8 min) Run:
   > /post a week of posts from inbox/post-ideas.txt, one per weekday
3. (5 min) Pick the best one and the worst one. Tell Claude what made the difference and save it to `notes/lessons.md`.
4. (2 min) Schedule them in your usual app, or set a daily reminder to paste one.

## With Claude Duet
Duet can remind you on posting days and draft a post from a photo you send it. Posting publicly should stay on "ask first".

## Done when
- [ ] Five posts in `outbox/` with suggested days
- [ ] One "what makes a good post for us" rule in `notes/lessons.md`
