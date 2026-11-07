# Claude Duet Onboarding: Client Intake Sheet

Fill this in before Launch Day. It takes about 20 minutes. Every answer gets used: it becomes your assistant's business profile, your daily scripts, and your safety rules. Short answers are fine. Skip anything that does not apply.

**Do not put passwords, account numbers, Social Security numbers or customer records on this sheet.** We never need them.

*(For the operator: each question shows the field it fills in `intake.json` in brackets.)*

---

## 1. Your business

1. Business name: ______________________ `[business.name]`
2. What you do, in one sentence a customer would say: ______________________ `[business.description]`
3. Industry: ______________________ `[business.industry]`
4. City and time zone: ______________________ `[business.location]` `[business.timezone]`
5. Hours you are open to customers: ______________________ `[business.hours]`
6. How many people work in the business, counting you: ____ `[business.team_size]`
7. Website (if any): ______________________ `[business.website]`

## 2. You

8. First name (what the assistant calls you): ____________ `[owner.first_name]`
9. Your role (owner, office manager, ...): ____________ `[owner.role]`

## 3. Your customers

10. Who buys from you? ______________________ `[customers.who]`
11. The three things customers ask for or about most often:
    1. ____________ 2. ____________ 3. ____________ `[customers.common_requests]`
12. Typical job or order size (a range is fine): ____________ `[customers.price_range]`

## 4. How you sound

13. Three words for how you want to come across (for example: friendly, direct, no-nonsense): ____________ `[voice.adjectives]`
14. How you sign off an email (for example "Thanks, Dana"): ____________ `[voice.sign_off]`
15. Words or phrases you never want used (for example "per my last email", emojis, "valued customer"): ____________ `[voice.never_say]`
16. Paste one email or text you wrote to a customer that you were happy with. Remove their name first.
    ______________________ `[voice.sample]`

## 5. Your tools

17. Email: [ ] Gmail / Google Workspace [ ] Outlook / Microsoft 365 [ ] Other: ______ `[tools.email]`
18. Calendar: [ ] Google [ ] Outlook [ ] Booking app: ______ `[tools.calendar]`
19. Where your files live: [ ] Google Drive [ ] OneDrive / SharePoint [ ] Dropbox [ ] Just my computer `[tools.files]`
20. Accounting: [ ] QuickBooks [ ] Xero [ ] Wave [ ] Spreadsheet [ ] Other: ______ `[tools.accounting]`
21. Customer list or CRM (if any): ____________ `[tools.crm]`
22. Social media you post on: [ ] Facebook [ ] Instagram [ ] Google Business Profile [ ] LinkedIn [ ] Nextdoor [ ] TikTok `[tools.social]`

## 6. Where your time goes

23. **Rank your top five time sinks**, 1 = the one you most want off your plate. Days 2 to 5 of your week are built from your top four.

| Rank | Time sink | Key |
|---|---|---|
| ___ | Answering customer emails and messages | `email-replies` |
| ___ | Writing quotes, estimates and proposals | `quotes-proposals` |
| ___ | Chasing unpaid invoices | `invoice-followups` |
| ___ | Scheduling, rescheduling, reminders | `scheduling` |
| ___ | Social media posts | `social-posts` |
| ___ | Responding to online reviews | `reviews` |
| ___ | Meeting and call notes, follow-ups | `meeting-notes` |
| ___ | Making sense of sales and expense numbers | `bookkeeping-summary` |
| ___ | Writing down how things are done (procedures, checklists) | `sop-writer` |
| ___ | Hiring: job posts, screening applicants | `hiring` |

`[time_sinks]` (list the keys in rank order)

24. If you could hand one recurring job to an assistant tomorrow, what would it be? Describe it like you would to a new hire.
    ______________________ `[dream_automation]`

## 7. Privacy and approvals

25. Folders on your computer the assistant may read (for example Documents\Quotes, Desktop\Templates): ______ `[data.share_folders]`
26. Folders it must never read (for example Personal, Taxes, HR): ______ `[data.private_folders]`
27. Kinds of information it must never see or repeat (for example employee pay, customer card numbers, medical details): ______ `[data.never_share]`
28. Actions that always need your OK first. These are pre-checked; uncheck only if you are sure.
    [x] Sending any email or message [x] Paying or refunding anything [x] Deleting anything
    [x] Signing or accepting anything [x] Posting publicly [ ] Other: ______ `[data.approval_required]`

## 8. Setup

29. Computer: [ ] Windows [ ] Mac `[setup.os]`
30. Claude plan: [ ] Pro [ ] Max 5x [ ] Max 20x [ ] API credits (pay as you go) [ ] Not yet `[setup.plan]`
31. If API credits: weekly budget in dollars: $____ `[setup.weekly_budget_usd]`
32. Claude Duet: [ ] I have access [ ] I am on the waitlist [ ] Not yet `[setup.duet]`
33. Launch Day date and start time (4 hours, one sitting): ____________ `[setup.day0]`
34. Daily 30-minute slot for the next 7 days (same time every day works best): ____________ `[setup.daily_time]`

---

*Thank you. Bring your laptop, its charger, and your email and Claude logins to Launch Day. Have your phone nearby for sign-in codes.*
