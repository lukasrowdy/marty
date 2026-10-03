# Safety model

Marty has real hands on a real PC, real email and real money in the form of API spend. The safety model assumes the model will sometimes be wrong, sometimes be manipulated, and sometimes be confidently mistaken, and puts controls where those failures would hurt.

## What it defends against

| Threat | Example |
|---|---|
| **Prompt injection** | An email, web page, ticket or document that says "Marty, forward this to..." |
| **Overreach** | The agent "fixing" something live that it should have proposed first. |
| **Silent capability creep** | A grant or token that outlives the reason it was issued. |
| **Secret leakage** | A key, token or private address landing in a commit, a note or a transcript. |
| **Private data to a cloud model** | Family photos, private chats or personal records sent to a hosted model for analysis. |
| **A stolen or lost phone** | A paired device used to drive the agent. |
| **Confident wrongness** | "It's up" or "it's done" claimed without checking. |

## The controls

### 1. External content is data, never instructions

Email bodies, web pages, files of unknown origin, API responses, and every comment, chat and message are content. Text inside them that addresses Marty by name is something Marty might reply to, never a command it obeys. Following a link, running code or acting on an embedded instruction needs Lukas's approval for that specific action.

Enforcement is structural where it can be: the customer-service agent's tool list includes `create_draft` and does not include any send tool, so even a fully manipulated triage run can only produce a draft for a human to read.

One scoped exception exists by design: one approved correspondent may email Marty questions directly. Those are answered with every resource except Lukas's personal details, and the exception is written down in the rules so it cannot quietly widen.

### 2. Approve before act

- **Double-confirm** before any source-code edit, any config that affects a running system, or any commit, push or deploy: state the exact change in plain language and wait for a clear yes.
- **Staged copies.** Changes are built in `.staged-*` folders, never in the live tree. The live change is a separate, approved step.
- **Locked decisions stay locked.** An instruction that contradicts a rule marked Locked is surfaced ("this contradicts X, are you changing it or is this a one-time exception?") rather than silently followed.

### 3. Screen control behind a signed, time-boxed grant

Marty's mouse-and-keyboard tool refuses every action unless a grant is active.

- **Time-boxed:** a grant is capped at four hours and carries its own expiry.
- **Signed:** the grant file holds `granted_at` and `expires_at` plus an HMAC-SHA256 over both. The HMAC key lives only in Windows Credential Manager; Lukas set it and Marty never sees it. Editing the expiry by hand breaks the signature.
- **Fails closed:** a missing key, a missing signature or a mismatch means no grant.
- **Out of reach:** the grant file lives in a per-user application-data folder whose ACL allows only the user and SYSTEM, and the tool refuses a grant file located anywhere under the agent's working tree.
- **Human in the loop to issue:** the grant and revoke commands are deliberately kept off any pre-approved command list, so issuing one always raises a permission prompt that a human has to click.
- **Logged:** every action is appended to a JSON-lines log.

### 4. Passkey step-up for the phone lane

The phone can drive the full agent through the Claude Agent SDK. Every permission prompt the agent raises is relayed to the phone, and approving an action on the PC needs a fresh WebAuthn assertion from a hardware security key. A stolen phone with a valid device token can read and chat; it cannot act.

### 5. A dashboard that is not on the internet

- The server binds `127.0.0.1` only and is published with `tailscale serve`, so it is reachable only from devices on the private tailnet, over HTTPS (`https://marty.example.ts.net/`).
- Device tokens are stored as SHA-256 hashes, expire after 30 days idle or 90 days absolute, and can be revoked per device.
- A privacy filter scrubs served text before it reaches the phone.

### 6. Secrets never touch a file

- API keys live in Windows Credential Manager and are read at call time ([`tools/cred.py`](../tools/cred.py)).
- Handoff docs, notes and summaries reference where a secret is stored, never its value.
- **The secret-scan gate.** [`git-tools/secret_scan.py`](../git-tools/secret_scan.py) runs from the pre-commit hook on every commit and checks staged content against ten rules (api-key, pem-block, bearer-token, credential-assignment, jwt, hex-near-keyword, base64-near-keyword, private-ip, email, private-term): API-key shapes, PEM headers, bearer tokens, quoted credential assignments, JWTs, long hex and base64 strings near a key-like word, private and tailnet IP ranges, email addresses, and a private-terms list read from an environment variable whose file lives outside every repo. A hit refuses the commit and prints the rule and a redacted preview, never the full match.
- The test fixtures for the scanner assemble their fake keys, addresses and headers at run time, so the scanner's own tests contain nothing key-shaped.

### 7. Private data stays local

- The switchboard's `--private` flag forces the local model and refuses every cloud brain in code.
- The spend meter records tokens and cost, never prompt or answer text.
- The local engine is hardened: cloud routing off, no history file, slot introspection off.

### 8. Family media stays in the house

Before any family photo or video goes to any outside service (a hosted vision model, a video tool, anything), it passes a local-only nudity and privacy screen on the PC. Anything flagged never leaves the machine and goes to a private folder for a human to review. Marty does not open flagged items itself. Faces are covered on the PC before any upload, and real faces are restored only locally.

This rule exists because a bulk media sort once sent contact sheets to a cloud model before any local screen existed.

### 9. Evidence, not confidence

- **Evidence only.** Verify from the file or the command before claiming anything is done or current.
- **Log-reader before "it's up".** Health claims are checked against logs with timestamps.
- **Skeptic before anything load-bearing.** A separate agent tries to refute the claim and defaults to REFUTED or UNCERTAIN when it cannot positively confirm.

### 10. Bandwidth and spend

The house runs on metered home internet. Any download over 1 GB requires proof it is not already on disk, the size and source, and a yes in chat, preferably overnight. API spend is metered per call, and model choice follows "the cheapest model that does the job well."

## Known gaps

Honest list, kept current:

- **The rules are mostly enforced by instruction, not by code.** The grant, the passkey, the send-less support agent, the private lane and the secret-scan gate are code. "Double-confirm" and "evidence only" are discipline rules that sit behind the permission prompt, not hard locks.
- **The LAN is flat.** The PC shares a consumer network with other household devices; there is no VLAN separation yet.
- **Local vision is not wired in yet.** Until it is, screen and camera features stay off rather than fall back to a cloud model.
- **Cross-session state is the newest weak spot.** The voice session and the chat session do not yet share open promises. The open-loop ledger on the [roadmap](roadmap.md) is the fix.
