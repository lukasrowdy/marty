# Architecture

Marty is Claude Code plus three things built around it: hands, memory, and the structure that aims the memory. This page walks the pieces in the order a request flows through them.

> The code published in this repo is excerpted from a private working repo and scrubbed for publication. Host names, addresses and paths below are placeholders (`marty.example.ts.net`, `192.0.2.10`, `you@example.com`, `<vault>`, `<agent root>`).

## 1. Surfaces: how Lukas reaches Marty

| Surface | Path |
|---|---|
| **Chat** | Claude Code on the desktop. The main session holds the conversation and the judgment calls. |
| **Phone dashboard** | An installable web app at `https://marty.example.ts.net/`, reachable only from devices on the private tailnet. |
| **Voice** | A spoken line: local speech-to-text, a hosted voice, and a brain on the Agent SDK. A private mode keeps the whole loop on the PC. |
| **Board taps** | Cards on the dashboard's Jobs tab. A tap is an answer; the next session reads the answers at boot and acts on them. |

All of them are the same Marty: same name, same rules, same vault.

## 2. The brain: one session, many helpers

The main session does not do administrative work. It holds the conversation, makes the calls, and reviews. Everything else goes to a subagent, each defined in [`.claude/agents/`](../.claude/agents/) with its own model and effort level:

- **Haiku** for mechanical extraction (scout, log-reader).
- **Sonnet** for ordinary builds and structured upkeep (vault-keeper, customer-service).
- **Opus** at high or extra-high effort for anything adversarial or security-shaped (skeptic, researcher, cyber-specialist).

Two dispatch rules keep this honest:

- **Confer before deciding.** Skeptic before anything expensive or irreversible, log-reader before any "it's up" claim, vault-keeper at checkpoints. The reply names who was consulted.
- **A queue over five deep gets delegated.** If more than five open items are not waiting on Lukas, helpers are dispatched in parallel, one item each, under the hard rules: staged copies only, no deploys, no messages, no secrets.

## 3. Memory: the vault

An Obsidian vault is the long-term memory. The session never tries to hold it; it holds the current job and loads the rest through indexes. See [vault-structure.md](vault-structure.md).

```
CLAUDE.md (pinned boot file, survives compaction)
   -> VAULT-INDEX.md (profile, full rules, system map)
        -> <Folder>.md index (one line per note)
             -> Job note (one per recurring job: steps, links, banked methods)
                  -> only the notes that job needs
```

The boot sequence reads the root index, yesterday's daily note, the open priorities, the board answers and any new uploads. After that, context is loaded just in time.

**Compaction is planned for, not feared.** Long sessions get summarized automatically. The boot file carries a "Compact Instructions" section that tells the summarizer what must survive (open questions to Lukas word for word, work in flight with exact paths, decisions with times), and Marty writes a "RESUME HERE" checkpoint after every finished job so a compaction at any moment loses nothing.

## 4. Hands

| Hand | Scope |
|---|---|
| **Files and documents** | Reads and writes in the project folders; builds `.docx` with [`tools/simple_docx.py`](../tools/simple_docx.py) (no third-party packages) and phone-fillable PDF forms. |
| **Email** | A Gmail connector. The support agent can create drafts and cannot send. |
| **Calendar** | Read, propose and create events. |
| **Browser** | Browser automation for research and the user's own sites. |
| **Screen control** | Mouse and keyboard on Windows, behind a signed, time-boxed grant. See [safety-model.md](safety-model.md). |

Every deliverable lands in a local project folder (never a cloud-synced one) and gets copied to the dashboard's outbox so it is on the phone too.

## 5. The switchboard

[`tools/switchboard.py`](../tools/switchboard.py) is one CLI and one import for every model:

```
py -3 tools/switchboard.py ask --to ollama|claude|grok|gemini|openrouter "question"
py -3 tools/switchboard.py ask --private "question about something private"
py -3 tools/switchboard.py ask --to claude --schema schema.json "extract these fields"
py -3 tools/switchboard.py spend
py -3 tools/switchboard.py selftest
```

- **Metered lanes** call the providers' HTTP APIs with keys read at call time from Windows Credential Manager ([`tools/cred.py`](../tools/cred.py)). No key ever sits in a file, an environment variable or a log.
- **Subscription lanes** shell out to `claude -p` and `codex exec` under flat-rate plans, locked to talk-only: no tools, no MCP, no browser, no session persistence, run from an empty temp directory.
- **The private lane** is a code path, not a convention. `--private` forces the local model and raises if a cloud brain is requested. Its transcript goes to a private folder kept off every sync path.
- **The meter** writes one JSON line per call: lane, model, tokens, cost. Never the prompt or the answer.
- **Structured output** takes one JSON Schema and translates it per provider, then validates the reply against the same schema.

**Lesson banked in the code:** Ollama replaces a Modelfile's `SYSTEM` block when a request carries its own system prompt; it does not append. The persona silently vanished on every call that set one. `model_system()` reads the baked-in prompt and prepends it.

## 6. Local models

Ollama runs on the PC's integrated Radeon 780M through Vulkan (no CUDA on this box). Marty's persona is baked into a local Modelfile so the local brain answers as Marty. The engine is hardened: cloud routing off, slot introspection off, no history file. A Qwen 3.5 vision model on the same machine reads a screenshot in about 3 seconds warm and about 40 seconds cold, which is the base for local-only vision on the roadmap.

## 7. The dashboard

A Python standard-library server bound to `127.0.0.1` only. It is published to the tailnet with `tailscale serve`, so it has a real HTTPS certificate on `marty.example.ts.net` and is not reachable from the LAN or the internet.

- **Tabs:** Chat, Jobs (the board), Files (the outbox), Talk, Status, Spend, Activity, and Galaxy (a 3D view of the vault's link graph).
- **Device auth:** pairing issues a device token; the server stores only its SHA-256 hash. Tokens expire after 30 days idle and 90 days absolute.
- **Privacy filter:** served text passes a scrub before it reaches the phone.

### Full Marty lane

The phone can also drive the whole agent, not just a chat model. It is built on the Claude Agent SDK's `ClaudeSDKClient`: every permission prompt the agent raises is relayed to the phone through the SDK's `can_use_tool` callback, and approving anything that acts on the PC needs a fresh WebAuthn passkey assertion from a hardware security key.

## 8. Keeping it alive

- **A supervisor** keeps the dashboard, voice and face processes running and restarts them on failure.
- **A house check** reports the state of each service; the preflight on the roadmap extends it to walk every chain end to end.
- **Backups:** a weekly mirror to a NAS, encrypted backups of private history, and a recovery-bundle drill.

## 9. Change control

- Code is never edited live. Changes are built in `.staged-*` copies, reviewed, skeptic-checked, and go live only on Lukas's explicit yes.
- Staged folders map to branches; deploys are tagged, so a rollback is a checkout.
- Every commit passes [`git-tools/secret_scan.py`](../git-tools/secret_scan.py) through the pre-commit hook, and the commit-msg hook refuses em dashes.

## Lessons that shaped the architecture

- **A capability that exists only on the command line does not exist.** A local model's tools were built and passed in a terminal, but the dashboard called it with no tools array, so on the phone it was talk-only. Done now means checked on the surface Lukas actually uses.
- **Test the artifact you ship.** A stylesheet passed as a separate file and broke once inlined, because a `</style>` sat inside one of its comments and HTML tokenizes before CSS parses. Build steps now get a guard that refuses to emit a bad artifact.
- **Deleting by pattern is a deploy.** Removing a spend-cap feature by cutting everything up to the next `def` also removed module constants that lived in between, and the switchboard went down. Deletions get the same review as additions.
