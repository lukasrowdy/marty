---
key: reviews
title: Responding to online reviews
command: review-reply
model: sonnet
---
## Why it matters
Future customers read how you answer reviews, especially the bad ones. A calm, specific reply within a day earns trust; a defensive one costs jobs. Claude keeps you calm and specific.

## Command
Draft a public reply to a review for {{business.name}}. The review: $ARGUMENTS

1. Classify it first: positive, mixed, or negative. If negative, list the specific complaints in one line each.
2. Reply rules:
   - Positive: thank them by first name only if the review shows it, mention one specific thing they said, invite them back. Three sentences at most.
   - Mixed or negative: thank them, acknowledge the specific issue without arguing, never admit legal fault or reveal private job details, offer to fix it offline [CHECK: phone or email to use]. Four sentences at most.
3. Voice: {{voice.adjectives}}. Never use: {{voice.never_say}}. No discounts or refunds unless `reference/` allows them.
4. If the review mentions injury, damage, a legal threat or discrimination, draft only a short holding reply and write ESCALATE at the top: {{owner.first_name}} decides.
5. Save to `outbox/review-replies-<date>.md`. Never post.

## Day task
**Goal: every unanswered review answered, and a house style for replies.**

1. (4 min) Copy your last five unanswered reviews (or five recent ones) into `inbox/reviews.txt`, with the star rating.
2. (8 min) Run:
   > /review-reply all reviews in inbox/reviews.txt, one reply each
3. (5 min) Read the negative-review replies twice. Would you be proud of them in a year? Adjust, and save what you changed as a rule.
4. (3 min) Post the replies yourself.

## With Claude Duet
If your review notifications arrive by email, Duet can flag new reviews and offer a draft. Posting stays "ask first".

## Done when
- [ ] A reply drafted for every review
- [ ] Your reply style rule in `notes/lessons.md`
