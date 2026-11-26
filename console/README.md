# Marty's band on Claude Managed Agents

These files define the band as hosted agents on the Claude Platform (the Console at platform.claude.com). Anthropic runs the agent loop and a cloud workspace for each session, so the band works without the PC being on.

| Agent | Role | Model |
|---|---|---|
| **marty** | Leader. Holds the conversation, delegates, merges, says who it consulted. | Opus 5.5, high effort |
| **skeptic** | Tries to refute one claim. | Opus 5.5, high effort |
| **researcher** | Primary-source research with confidence levels and dead ends. | Opus 5.5, extra-high effort |
| **cyber-specialist** | Security and GRC: tutoring, SOC reports, security review. | Opus 5.5, high effort |

Marty can spawn the three specialists in their own threads, and can start **workflow runs** (many researcher or skeptic copies working through a big job in parallel). Every agent in a run uses tokens, so start sessions with a budget. To turn runs off, set `workflows: {type: disabled}` in `agents/marty/agent.md`.

Tools run under `auto`: the server judges each call and runs it, denies it, or pauses for your answer.

## Not here yet

- **customer-service** needs a Gmail connection (an MCP server URL plus a credential in a vault). It stays in Claude Code until that is chosen.
- **scout, log-reader, vault-keeper** read the vault and logs on the PC. A cloud workspace can't see them. They stay in Claude Code, or move later through a self-hosted environment that runs tools on the PC.

## Option A: create them in the Console

Follow [CONSOLE-PASTE.md](CONSOLE-PASTE.md): create skeptic, researcher and cyber-specialist first, copy each `agent_...` ID, then create marty with those IDs in its roster. Create one cloud environment with unrestricted networking (the specialists read the open web). Agents made this way cannot later be managed by `ant apply`, so pick one route.

## Option B: sync from these files with the `ant` CLI

Needs `ant` 1.40.0 or later (`brew install anthropics/tap/ant`) and `ant auth login`. Run from this `console/` folder:

```sh
ant apply --dry-run -v agents/marty/agent.md agents/marty/environment.yaml
ant apply agents/marty/agent.md agents/marty/environment.yaml
```

Marty's file references the three specialists by path, so one apply creates all four agents and the environment, and writes their IDs to `claude-lock.json` (commit it). To change an agent later, edit its file and apply again.

## Run a test session

```sh
AGENT_ID=$(jq -r '.resources["./agents/marty/agent.md"].id' claude-lock.json)
ENV_ID=$(jq -r '.resources["./agents/marty/environment.yaml"].id' claude-lock.json)
SID=$(ant beta:sessions create --agent "$AGENT_ID" --environment-id "$ENV_ID" \
  --budget '{type: limit, max_list_cost: {amount: "500", currency: USD}}' \
  --title "Band test" --transform id -r)
ant beta:sessions connect "$SID" --web
```

The budget is a hard $5.00 cap for the whole session, all threads included. A good first message: "Is Ollama's Vulkan backend still the best way to run a 12B model on my Radeon 780M? Have skeptic check the answer."
