# Roadmap

What's next, in build order, with the reason for each. Everything here follows the same change control as the rest of Marty: built in a staged copy, skeptic-checked, live only on Lukas's yes.

## 1. Open-loop ledger shared across sessions

**Why:** a real failure on 2026-10-02: the voice session did not know what the chat session had promised. Each session had its own context, and nothing shared open promises between them.

**What:** one small vault note, kept under about 3 KB, with three sections:

- **Open questions to Lukas,** word for word, with when they were asked.
- **Promises,** each with an ETA and the session that made it.
- **Waiting on others,** with who and since when.

Every surface (chat, voice, phone) reads it before answering anything about state, and writes to it the moment it asks a question or makes a promise. Closing an item deletes it. The note stays small on purpose: it is read on every turn.

## 2. End-to-end preflight health check

**Why:** "it's up" has been wrong before, in both directions. A process can be running while the chain the user depends on is broken, and a service can be marked down while its log shows it live.

**What:** one command that walks each chain the way Lukas uses it and prints one PASS or FAIL line per chain, with the reason:

- the dashboard over the tailnet (`https://marty.example.ts.net/`), with a real HTTPS request
- the voice line
- the face server
- Ollama, with a real generation
- every switchboard lane, with a real one-line call
- the mail connector
- the outbox, writable

It extends the existing house check rather than adding a second checker, so there is still only one place to look.

## 3. Eyes for the voice line, on local-only vision

**Why:** screen features are useful, and they are exactly the frames that should never leave the PC.

**What:** the voice session gets a look tool. A screenshot goes to the Qwen 3.5 vision model already on the PC, which reads it correctly in about 3 seconds warm (about 40 seconds cold), and the answer comes back spoken. Screen frames never leave the PC. There is no cloud fallback: if the local model is down, the tool is off.

## 4. A phone line

**Why:** the voice line works at the desk and over the phone app, but Lukas also wants to simply call Marty.

**What:** calls run through Retell. Strangers reach a message-taker with no memory and no access to anything. Lukas reaches Marty's real brain, running talk-only (it can read the vault and nothing else), through a single secret-path tunnel, gated on caller ID plus a spoken PIN. Everything said on a call is treated as outside content, never as instructions.

## 5. Gesture control of the vault galaxy

**Why:** the dashboard's Galaxy tab renders the vault's link graph in 3D. Navigating it by hand gesture is the most direct way to move through memory on a big screen.

**What:** a clean-room build on Google's MediaPipe hand tracking (Apache-2.0), self-hosted so no frame or model call leaves the PC. Camera opt-in. The idea came from a third-party skill pack that ships without a license, so none of its code is used; this is written from the described behavior only.

## 6. Overnight Qwen 3.8 27B local-brain test

**Why:** the open question is how much of Marty could run with no cloud at all, on hardware with no discrete GPU.

**What:** an overnight run pulls the 27B model (about 18 GB, scheduled for the overnight window because the house is on metered internet) and benchmarks it against the current local models on Marty's real task types: speed, tool use, instruction following, and quality on a fixed set of prompts. The result decides whether a dedicated local machine is worth it, and the answer depends on whether client work needs fully local inference.

## On the list, not yet scheduled

- **A particle face** driven by the voice, replacing the current animated face.
- **A focus timer** for study blocks, tied to the study plan.
- **Network segmentation** so the PC no longer shares a flat LAN with other household devices.

## Considered and skipped

Some ideas were evaluated and deliberately not built: chat-app bridges, and public tunnels to the dashboard. Each would have widened the attack surface or sent private data off the PC for a convenience the tailnet already provides.
