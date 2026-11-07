# Marty

**A personal AI operator built on Claude Code.**

Marty is an operator, not a chatbot. Ask a chatbot something and you get an answer. Ask Marty and you get the thing done: the email drafted, the document built, the broken service running again.

There is no special model underneath. Marty runs on Claude, the same model anyone can use. What makes the difference is what is wired around it:

1. **Reach.** Marty is connected to real files, accounts and machines, with permission gates on anything that matters, so it finishes work instead of describing it.
2. **A memory outside the model.** Everything Marty learns goes into an Obsidian vault that grows without limit. Marty never loads all of it. It knows what exists and pulls in the one piece a task needs.
3. **An index that makes the memory usable.** Every folder has an index, and every recurring job has one master note pointing at exactly what that job needs, so the right context arrives in one step.

Each session starts with no recollection of the last one. What carries over is the vault and the rules: every mistake that got corrected was written back as a rule or a note, so the next session starts out already knowing better.

![How Marty works: Lukas talks to Marty over chat, a phone dashboard or voice. Marty holds the judgment calls and delegates to a team of subagents, reads and writes memory in an Obsidian vault, acts through its hands, routes model calls through a multi-provider switchboard, and runs inside guardrails each learned from a real miss.](docs/how-marty-works.png)

---

## The key ideas

### 1. The vault is the memory

An Obsidian vault holds everything Marty knows: profile, rules, projects, component notes and a daily log. A pinned boot file (`CLAUDE.md`) loads at the start of every session and survives context compaction; it carries the identity and the rules that can never lapse, and points at the vault's root index for everything else.

- **Indexes are a contract.** Every folder has an index note listing each note in it with one line. A note the index does not show is a note no future session will find, so the index is updated in the same pass as the note.
- **One master note per recurring job.** When Lukas explains how to do something once, it becomes a Job note. The next time the job comes up, Marty loads that one note and the notes it links to, and nothing else.
- **Checkpoints, not hope.** After every finished job, and before any long read, Marty writes a "RESUME HERE" checkpoint to the daily note. A context compaction at any moment then loses nothing.

Details: [docs/vault-structure.md](docs/vault-structure.md).

### 2. Rules that can't lapse

A short list of rules lives in the boot file because it has to survive every compaction. Some came with the starting template; the ones with a story were earned here. A few of them:

- **Evidence only, never guess.** Verify state from the actual file or command before claiming anything is done.
- **Double-confirm before any source-code edit, config change or deploy.** State the exact change in plain language and wait for an explicit yes.
- **Close the loop.** When Marty asks Lukas a question, it stops and waits. Re-stating the question at the top of a reply while charging ahead underneath is the exact failure the rule exists to stop.
- **Test the artifact you ship, not the one you built it from.** A stylesheet passed every test as a separate file, then a `</style>` inside one of its own comments truncated it once it was inlined into a single-file bundle. Only the shipped form counts.

All of them, generalized, with the lesson behind each: [docs/rules.md](docs/rules.md).

### 3. A team that argues

Lukas did not want one voice deciding alone. Marty holds the conversation and the judgment calls; seven subagents do the rest, each with its own model and effort level chosen for the work:

| Agent | Job | Model |
|---|---|---|
| **skeptic** | Tries to refute a claim before anything expensive, irreversible or load-bearing happens. Defaults to REFUTED or UNCERTAIN when it cannot positively confirm. | Opus, high effort |
| **researcher** | External primary sources only, with confidence levels and an explicit dead-ends list. | Opus, extra-high effort |
| **cyber-specialist** | Security and GRC depth: security review of Marty's own builds, SOC report reading, tutoring. | Opus, high effort |
| **scout** | Finds things on disk and returns paths and excerpts, never opinions. | Haiku |
| **log-reader** | What actually happened, with timestamps, before anyone claims a service is healthy. | Haiku |
| **vault-keeper** | Keeps the memory map true: index drift, frontmatter, broken links. | Sonnet |
| **customer-service** | Triages a support queue and writes Gmail drafts. It has no send tool at all. | Sonnet |

Conferring is a rule, not a habit: the skeptic before anything expensive or irreversible, the log-reader before any "it's up" claim, the vault-keeper at checkpoints, and every reply says who was consulted and what they found. Consulting silently counts as not consulting. The definitions are in [.claude/agents/](.claude/agents/).

### 4. One switchboard, every provider, private data local-only

[tools/switchboard.py](tools/switchboard.py) is one door to every model:

- **Metered API lanes:** Claude (Anthropic), Grok (xAI), Gemini (Google), and OpenRouter (about 440 models, including OpenAI's).
- **Local lane:** Ollama on the PC's integrated AMD GPU through Vulkan. $0, and nothing leaves the machine.
- **Subscription lanes:** `claude -p` and `codex exec` shelled out from flat-rate plans, locked down to talk-only.
- **A private lane enforced in code.** `--private` forces the local model and refuses every cloud brain by code, not by convention, and logs only to a private folder kept off every sync and backup path.
- **A spend meter** that records tokens and cost per call but never the prompt or answer text, so it is safe to keep even for private calls.
- **Structured output** from one JSON schema, normalized per provider (forced tool use for Claude, `response_format` for the OpenAI-shaped lanes, `responseSchema` for Gemini, `format` for Ollama).

Every night, every lane gets at least one real task, public data only on the cloud lanes. The rule for model choice is the cheapest model that does the job well, with the top tier reserved for load-bearing work.

### 5. A safety model built from real misses

| Control | How it is enforced |
|---|---|
| **Approve before act** | Code, config and deploys are built in staged copies and go live only on Lukas's explicit yes. A git pre-commit gate and deploy tags make every change reversible. |
| **Signed, time-boxed screen control** | Marty's mouse-and-keyboard tool refuses every action unless a grant is active. The grant is capped at four hours, HMAC-signed with a key that lives only in the OS credential store (Marty never sees it), stored outside the agent's working tree, and fails closed on any missing or tampered signature. Issuing one always hits a human permission prompt. |
| **Passkey step-up** | The phone lane that drives the full agent relays every permission prompt for approve or deny, and acting on the PC requires a fresh passkey assertion from a hardware security key. |
| **Secret-scan gate** | [git-tools/secret_scan.py](git-tools/secret_scan.py) runs on every commit: key shapes, PEM headers, bearer tokens, JWTs, private and tailnet IP ranges, emails, and a private-terms list kept outside every repo. |
| **External content is data** | Email bodies, web pages, tickets and comments are never instructions, even when they address Marty by name. The support agent has a draft tool and no send tool. |
| **Family media stays in the house** | Before any family photo or video goes to any outside service, it passes a local-only privacy screen on the PC. Anything flagged never leaves, and Marty does not open flagged items itself. |

The full threat model and the known gaps: [docs/safety-model.md](docs/safety-model.md).

---

## What's built

| Piece | What it does |
|---|---|
| **Boot config + vault** | Pinned identity and rules, an Obsidian vault with folder indexes, Job notes and daily notes, and checkpoint discipline that survives context compaction. |
| **Agent roster** | Seven subagents with per-role models, conferred with before any solid decision. |
| **Switchboard** | Five metered and local brains plus three subscription lanes, a code-enforced private lane, spend metering and per-provider structured output. |
| **Local models** | Ollama on a Radeon 780M iGPU through Vulkan, with Marty's persona baked into a Modelfile and the local engine hardened (no slot introspection, no history, no cloud routing). |
| **Dashboard (phone app)** | A standard-library Python server bound to loopback, reached only over HTTPS inside a private Tailscale network. An installable app with Chat, a Jobs board Lukas answers by tapping, Files, Talk, Status, Spend, Activity, and a Galaxy view of the vault. Hashed device tokens that expire. |
| **Full Marty lane** | The whole agent from the phone, built on the Claude Agent SDK: permission prompts relayed to the phone, with a hardware-key passkey step-up. |
| **Voice and face** | A spoken line (local Whisper ears, an ElevenLabs voice, an Agent SDK brain, and a private mode that stays local) and an animated face driven by the voice audio. |
| **Hands** | Low-level Windows input control behind the signed, time-boxed grant, with every action logged. |
| **Supervisor + backups** | A service supervisor that keeps the dashboard, voice and face alive; a weekly NAS mirror, encrypted backups and a recovery-bundle drill. |
| **Marty Jr** | A separate, fully local model lane with its own encrypted history and supervised eyes and hands inside a VM. |
| **Git discipline** | A secret-scan pre-commit gate, a commit-message hook, staged folders that become branches, and deploys that become tags so rollback is a checkout. |

It all runs on one small-form-factor Windows 11 desktop: a Ryzen 7 250, 62 GB of RAM, and no discrete GPU.

---

## What's next

The full list, with the reasoning, is in [docs/roadmap.md](docs/roadmap.md).

1. **An open-loop ledger shared across sessions.** Born from a real failure on 2026-10-02: the voice session did not know what the chat session had promised. One small vault note holds the open questions to Lukas, the promises with an ETA, and what is waiting on someone else. Every session reads it before answering anything about state, and writes to it the moment it asks a question or makes a promise.
2. **An end-to-end preflight health check.** One check that walks every live chain the way Lukas actually uses it (the dashboard over the tailnet, the voice line, the face server, Ollama, every switchboard lane, the mail connector, the outbox) and prints one PASS or FAIL line per chain with the reason. It extends the existing house check rather than adding a second checker.
3. **Eyes for the voice line, on local-only vision.** The voice session gets a look tool: a screenshot goes to the Qwen 3.5 vision model already on the PC (about 3 seconds warm) and the answer comes back spoken. Screen frames never leave the PC.
4. **A phone line.** Calls run through Retell. Strangers reach a message-taker with no memory. Lukas reaches Marty's real brain, running talk-only (it can read the vault and nothing else), through a single secret-path tunnel, gated on caller ID plus a spoken PIN. Everything said on a call is treated as outside content, never as instructions.
5. **Gesture control of the vault galaxy.** A clean-room rebuild on self-hosted MediaPipe: the camera is opt-in and nothing is sent anywhere.
6. **The overnight Qwen 3.8 27B local-brain test.** Pulled and benchmarked overnight against the current local models, to answer how much of Marty could run with no cloud at all.

---

## Teaching it: the Claude Duet onboarding class

[onboarding/](onboarding/) packages what Marty taught into a one-week class for small-business owners: a 4-hour Launch Day, then 30 minutes a day, one task a day, for 7 days. An intake sheet feeds a kit builder that writes each client's Claude Code workspace (business profile, voice, a slash command per time sink, deny rules, a credit plan sized to one week), and a local sanitization check screens every folder before Claude reads it. Details: [onboarding/README.md](onboarding/README.md).

---

## What's in this repo

This is a showcase, not the working system. The published code is excerpted from a private working repo and scrubbed: machine paths are environment variables or placeholders, credential-store target names are generic, and anything personal is gone. The logic is unchanged.

```
README.md                    this page
docs/
  architecture.md            how the pieces fit, and the lessons that shaped them
  safety-model.md            threat model, controls, and known gaps
  rules.md                   the rules that can't lapse, generalized, with the lesson behind each
  vault-structure.md         the folder skeleton and how indexes, Jobs and daily notes work
  roadmap.md                 what's being built next
  how-marty-works.png/.html  the one-page diagram and its source
tools/
  switchboard.py             one door to every model, with the private lane and the spend meter
  cred.py                    Windows Credential Manager store the switchboard reads keys from
  simple_docx.py             a .docx writer with no third-party packages
git-tools/
  secret_scan.py             the pre-commit secret scan
  install_hooks.py           points core.hooksPath at git-tools/hooks
  hooks/pre-commit           runs the scan on staged files and refuses the commit on a hit
  hooks/commit-msg           refuses an empty subject or an em dash
  test_secret_scan.py        28 tests: every rule both ways, ignore file, config, end to end
  test_install_hooks.py      6 tests: install, idempotence, and real commits through the hooks
.claude/agents/              the seven subagent definitions
onboarding/                  the Claude Duet onboarding class: intake, curriculum, script library,
                             kit builder, local sanitization check, and their tests
```

Try it (Windows, Python 3.12):

```
py -3.12 tools/switchboard.py selftest
py -3.12 -m unittest discover -s git-tools -p "test_*.py"
py -3.12 git-tools/install_hooks.py
```

---

## Credits

Marty stands on other people's open work. None of their code is included here; go to the source:

- **[fullstack-agent](https://github.com/jaredrhod/fullstack-agent)** by Jared Rhodenizer (AGPL-3.0): the starting kit for memory, voice and face.
- **[backtalk](https://github.com/jaredrhod/backtalk)** (AGPL-3.0): the voice line.
- **[ai-visualizer](https://github.com/jaredrhod/ai-visualizer)** (AGPL-3.0): the animated face.
- **[ai-memory-vault](https://github.com/jaredrhod/ai-memory-vault)** (CC BY-SA 4.0): the vault pattern Marty's memory grew from.
- **[FaceFusion](https://github.com/facefusion/facefusion)** (OpenRAIL-AS): local face restoration, so real faces only ever go back on the PC.
- **Brain-Jarvis V7**, a skill pack that ships without a license, so all rights stay with its author. Marty borrows ideas from its described behavior only, as clean-room rewrites, and none of its code.
- **[Claude Code](https://claude.com/claude-code)** and the **Claude Agent SDK** by Anthropic, **[Ollama](https://ollama.com)**, **[Obsidian](https://obsidian.md)** and **[Tailscale](https://tailscale.com)**.

---

## Author

**Lukas Alvarez.** A business owner, fireman and former Army flight medic, now studying cybersecurity, who built Marty with Claude Code.

License: not yet chosen, all rights reserved for now, except docs/rules.md, which adapts CC BY-SA 4.0 material and is shared under CC BY-SA 4.0.
