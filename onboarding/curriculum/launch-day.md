# Launch Day run sheet (4 hours)

This is the operator's script for the one live session. The client's copy of the agenda is in their kit's `WEEK-PLAN.md`. Times are elapsed from the start. Every block lists what to say, what to do, and the checkpoint that has to be true before moving on.

**Before you arrive (20 minutes, the day before)**
- [ ] Intake reviewed. Anything vague? Text the client one question, not ten.
- [ ] `python3 build_kit.py intake/clients/<client>.json` ran clean. Read `WEEK-PLAN.md` once.
- [ ] Kit zipped onto a USB stick and in your cloud drive (you will need one or the other).
- [ ] Client reminded: laptop, charger, email and Claude logins, phone for sign-in codes.
- [ ] If the client has no Claude plan yet: they buy Pro before you arrive (Duet requires Pro or Max).

---

## 0:00 to 0:20: Welcome, goals, the three rules

**Say:** "By the end of today you will have an assistant that knows your business, writes in your voice, and has already done one real job for you. Then it is 30 minutes a day for a week, one task each day. You never need me in the room again."

**Do:**
1. Ask: "If this works, what will be different by next Saturday?" Write the top 3 answers on paper. These go in `notes/daily-log.md` later.
2. Teach the three rules, one sentence each. They are in `START-HERE.md`:
   - **Claude drafts, you send.** Nothing leaves without you.
   - **Check a folder before Claude sees it.** That is what the sanitization check is for.
   - **Correct it once, write it down.** Mistakes become rules in `notes/lessons.md`.
3. Explain the two tools in one breath: **Claude Duet** watches your email and calendar and asks before acting; **Claude Code** is the workshop on your computer where you build the jobs. This week is mostly Claude Code, because that is where the skills get built.

**Checkpoint:** three goals written down; the client can repeat the three rules.

## 0:20 to 0:50: Install and sign in

**Do (Windows):**
1. Open Windows Terminal (or PowerShell).
2. Install Claude Code with the native installer from the official docs (code.claude.com/docs; at the time of writing: `irm https://claude.ai/install.ps1 | iex`).
3. Install Python if `py --version` fails: `winget install -e --id Python.Python.3.12`. Close and reopen the terminal.
4. Unzip the kit to `Documents\Claude-Workspace`.

**Do (Mac):**
1. Open Terminal.
2. Install Claude Code with the native installer from the official docs (at the time of writing: `curl -fsSL https://claude.ai/install.sh | bash`).
3. If `python3 --version` fails: `xcode-select --install`.
4. Unzip the kit to `~/Documents/Claude-Workspace`.

**Then (both):**
1. `cd` into the workspace, type `claude`, sign in with the client's Claude account.
2. Type `/status` and check the model reads Sonnet (the kit's default).
3. Type: `What is in CLAUDE.md? Answer in three lines.` If Claude describes their business, the kit is live.
4. Show `/` (the command list), `/clear`, `/usage` (or `/cost` on API credits), and Esc to stop Claude mid-answer.

**Checkpoint:** Claude Code answers from `CLAUDE.md`. `py tools/sanitize_check.py --list-rules` (Mac: `python3 ...`) prints the rule list.

**If it goes wrong:** see Troubleshooting at the bottom. Do not burn more than 10 minutes here: if install is stuck, run the rest of the day from your own laptop with their kit and finish the install at the end.

## 0:50 to 1:15: Sanitization check on their files

**Say:** "Before Claude reads anything of yours, we check it on your own machine. Nothing leaves this laptop during the check."

**Do:**
1. From the intake, open each folder in `data.share_folders`. Run the check on each:
   ```
   py tools/sanitize_check.py "$env:USERPROFILE\Documents\Ridgeline\Quotes" --report notes\sanitize-report.md
   ```
   (Mac: `python3 tools/sanitize_check.py ~/Documents/Ridgeline/Quotes --report notes/sanitize-report.md`.)
2. Walk the verdicts with the client:
   - **BLOCK**: move the file out to their private folder now. If it held a password or key, write "rotate" on the paper list; that is their homework, not today's.
   - **REVIEW**: one decision per file: keep, trim, or move. A customer list is usually "keep" for email work.
   - **SKIPPED**: PDFs and images were not read. Ask: "Is there anything private in these?" If unsure, leave them out.
3. **Copy in, do not point at.** Copy the files Claude needs (a price sheet, two past quotes, a few templates) into the workspace's `reference/`, `templates/` or `inbox/`. Claude works on copies inside the workspace, not on their live folders.
4. Run the check once more on the whole workspace: `py tools/sanitize_check.py . --deny-settings .` This also adds deny rules for anything still flagged BLOCK. Explain that the deny rule is a seatbelt; moving the file out is the fix.

**Checkpoint:** the workspace scan shows 0 BLOCK. The report is in `notes/`.

## 1:15 to 1:25: Break

## 1:25 to 1:55: Walkthrough 1: the business profile

**Say:** "This file is everything Claude knows about your business before you say a word. Let's make it right."

**Do:**
1. Open `CLAUDE.md` with the client. Read the business section aloud. Fix anything wrong by asking Claude, not by editing by hand, so they learn the move:
   > In CLAUDE.md, change the hours to Monday to Friday 8 to 6 and Saturday 9 to 2.
2. Fill the price list. It ships as a stub with [CHECK] marks:
   > Interview me about reference/prices-and-services.md. Go through every [CHECK] one at a time, then rewrite the file. Do not invent anything.
3. Test the profile with a question a customer would ask:
   > A customer asks: how much for <their most common request>, and can you come Thursday? Answer as me, in a draft, using only the files.

   Point out: the draft used their price, their voice, their sign-off, and a [CHECK] where it did not know their calendar. That [CHECK] is the safety net working.

**Checkpoint:** no [CHECK] left in the price list (or the client knows which ones are open), and the test draft sounds like them.

## 1:55 to 2:25: Walkthrough 2: the morning brief

**Do:**
1. Put three real things into `inbox/`: copy two emails into `inbox/emails.txt`, and type their to-do list into `inbox/todo.txt`.
2. Type `/today`. Read the brief together.
3. Correct one thing deliberately (there is always one), then:
   > Add that to notes/lessons.md.
4. Run `/today` again. Let them see the change.
5. Add today's entry to `notes/daily-log.md` with the three goals from 0:00.

**Say:** "That loop, correct once, write it down, is the whole method. You will do it every day this week."

**Checkpoint:** a brief in `outbox/`, one line in `notes/lessons.md`.

## 2:25 to 2:55: Walkthrough 3: their top time sink

The kit's `WEEK-PLAN.md` names it (their #1 ranked time sink). The script is Day 2's task in the same file; today you run it **with** them, Day 2 they run it **alone**.

**Do:**
1. Use real material: real emails, a real quote request, real reviews. Real work is what makes the course stick.
2. Run the command (for example `/reply inbox/emails.txt`). Narrate what Claude is doing.
3. Have the client read the result and send it themselves from their usual email or app.
4. Ask: "How long would that have taken you?" Write the answer in `notes/daily-log.md` as minutes saved.

**Checkpoint:** one real piece of work sent by the client.

## 2:55 to 3:05: Break

## 3:05 to 3:25: Claude Duet

Claude Duet is Anthropic's proactive assistant (a research preview at the time of writing, for Pro and Max subscribers, with a waitlist). It works from connected email and calendar, sends a morning summary, and asks before it sends, pays, signs or deletes anything. Menus change during a preview; follow what the app shows.

**If the client has access:**
1. Open Duet (phone app or claude.ai) with them.
2. Connect email and calendar only. Leave other connections for after the week.
3. Find the approval settings and confirm: ask before sending, paying, signing, deleting, posting. Match `data.approval_required` from the intake.
4. Tell Duet the business basics in the same words as `CLAUDE.md`'s first section, and the voice rules.
5. Set the morning summary to arrive before their daily slot.

**If waitlisted or not yet:** nothing is lost. `/today`, `/reply` and `/schedule` cover the same ground from files in `inbox/`. Show them where the waitlist status appears, and tell them the Day 7 check-in is when you connect it if access arrives this week.

**Checkpoint:** Duet connected with approvals on, or the client knows the fallback.

## 3:25 to 3:40: Credit and usage

**Do:** open the kit's `budget.md` together.
1. Show where usage lives: `/usage` on Pro or Max, `/cost` and the Console on API credits.
2. The five habits, especially **one task per session, then `/clear`**.
3. Say what happens at a limit: work in `outbox/` is safe; continue after the reset.

**Checkpoint:** the client checks their own usage without help.

## 3:40 to 4:00: The week ahead and Q&A

**Do:**
1. Walk Days 1 to 7 in `WEEK-PLAN.md` in two minutes: same slot daily, 30 minutes, one task.
2. Put the daily slot on their calendar now, all seven days, with "open WEEK-PLAN.md, Day N" in the event.
3. Tell them how check-ins work (see `daily-sessions.md`): you send a short message each day; they reply with their Done-when boxes.
4. Q&A. Park anything big for Day 6 ("that sounds like your own command").

**Checkpoint:** seven calendar events exist. Client knows Day 1 is tomorrow.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `claude` not found after install | Close and reopen the terminal. On Windows, sign out and back in if it persists. |
| `py` or `python3` not found | Install as in 0:20, reopen the terminal. On Windows, `python` may work where `py` does not. |
| Sign-in loops or fails | Use the browser that is signed in to claude.ai. Check the account has a Pro, Max or API plan. |
| Claude ignores `CLAUDE.md` | Claude was started outside the workspace. `cd` into it and start again. |
| A slash command is missing | The kit's `.claude/` folder was not copied (hidden folders get dropped by some unzip tools). Re-extract with the system's own unzip. |
| Usage limit hit on Launch Day | Do the non-Claude parts (sanitization decisions, Duet settings, calendar) and resume after the reset. |
| Documents is synced to OneDrive (Windows) | The private-folder deny rules use `~/Documents/...`. If Documents lives under OneDrive, add matching rules for the real path in `.claude/settings.json`. |
| The check flags something that is fine | Leave it flagged and decide in the report. For a known-safe line in a text file, add the comment `secret-scan: allow` to that line. |
