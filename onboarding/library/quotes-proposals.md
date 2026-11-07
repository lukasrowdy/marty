---
key: quotes-proposals
title: Quotes and proposals from a template
command: quote
model: sonnet
---
## Why it matters
A quote that goes out the same day wins more often than a better quote that goes out on Friday. One good template plus your price list turns a 30-minute quote into a 3-minute review.

## Command
Write a quote for {{business.name}}. Job details: $ARGUMENTS

1. Use `templates/quote-template.md` as the layout. If it does not exist, stop and offer to build it with {{owner.first_name}} first.
2. Prices come only from `reference/prices-and-services.md`. Never invent a price, discount or deadline. Anything missing becomes [CHECK: ...].
3. Show the math: line items, quantities, unit prices, subtotal, tax if the reference says how, total. Double-check the arithmetic and say "math checked" at the end.
4. Save to `outbox/quote-<customer>-<date>.md`, then write a 3-line cover email in {{owner.first_name}}'s voice ({{voice.adjectives}}, signed "{{voice.sign_off}}").
5. List assumptions you made, so {{owner.first_name}} can confirm them before sending.

## Day task
**Goal: build your quote template once, then produce a real quote in under 5 minutes.**

1. (8 min) Put two quotes you have sent before into `inbox/` (remove customer names). Then:
   > Look at the two quotes in inbox/. Build templates/quote-template.md with my business details, the sections I always use, and placeholders for everything that changes. Ask me about anything that differs between the two.
2. (7 min) Take a real request that is waiting on you, or invent a typical one:
   > /quote {{customers.common_requests.0}} for a new customer, normal size job
3. (5 min) Check the line items against what you would have charged. Correct anything and save the rule (for example "travel over 20 miles is $1 per mile") to `reference/prices-and-services.md`.

## With Claude Duet
When a quote request lands in your inbox, Duet can flag it and ask if you want a quote prepared. Point it at the same template and price list. It should never send a quote without your approval; check that setting.

## Done when
- [ ] `templates/quote-template.md` exists
- [ ] One quote and cover email in `outbox/`, math checked
- [ ] Any new pricing rule is written into `reference/`
