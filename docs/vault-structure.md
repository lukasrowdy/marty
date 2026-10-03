# Vault structure

Marty's memory is an Obsidian vault: plain Markdown files with `[[wikilinks]]`. The vault itself is private and is not in this repo. This page shows its skeleton and conventions, with made-up example notes.

## Folder skeleton

```
<vault>/
  VAULT-INDEX.md                 root index: profile, full rules, system map
  00 - Inbox/                    unsorted captures, triaged into a home
    00 - Inbox.md
  01 - Daily Notes/              append-only session log
    01 - Daily Notes.md
    Daily Note Template.md
    09 - September 2026/
      2026-09-30.md
    10 - October 2026/
      2026-10-01.md
  02 - School/                   coursework, study plans, quizzes
    02 - School.md
  03 - Cybersecurity/            career track, reference library, security plans
    03 - Cybersecurity.md
  04 - Construction/             business work
    04 - Construction.md
  05 - Personal/                 personal admin
    05 - Personal.md
  06 - Archive/                  finished or superseded notes
    06 - Archive.md
  07 - Resources/
    07 - Resources.md
    Jobs/                        one master note per recurring job
      Jobs.md
    Marty Stack/                 one note per component of Marty itself
      Marty Stack.md
```

## The three kinds of index

1. **`VAULT-INDEX.md`** is the root. It holds the profile, the full rules and the map of every folder. It is read at the start of every session.
2. **Folder indexes** (`<Folder Name>.md`) list every note in their folder with one line each. They are a contract: a note the index does not show is a note no future session will find, so the index is updated in the same pass as any note created, renamed, moved or materially changed. A new folder gets its index and a line in the root map at the same time.
3. **Job notes** are the precision layer. Each recurring job gets one master note that says how to do it and links exactly the notes it needs.

## Frontmatter

Every note carries three fields with a fixed set of values, so the vault-keeper agent can check them mechanically:

```yaml
---
status: active        # active | done | archived | reference
project: school       # one of a short, fixed list
type: job             # job | note | daily | index | reference
---
```

## A Job note (made-up example)

```markdown
---
status: active
project: school
type: job
---
# Grade a Practice Quiz

**When:** Lukas sends a finished practice quiz.

**Load:** [[Study Plan]], [[Quiz Answer Key Format]], this note. Nothing else.

## Steps
1. Read the whole quiz, every question, before grading any of it.
2. Grade against the held-back key. Mark each miss with the objective it maps to.
3. Write the score and the weak objectives to [[Study Plan]].
4. Build the review as a .docx and copy it to the outbox.

## Banked methods
- 2026-09-14: the quiz PDF has form fields; read the field values, not the page
  text, or the answers come back empty. (Dead end: page-text extraction.)
```

The "Banked methods" section is how the vault gets smarter: when a recurring job fails on the first approach and another works, the winner and the dead end go here before moving on.

## A daily note (made-up example)

Daily notes live in monthly folders (`NN - Month YYYY`), are named `YYYY-MM-DD.md`, and are always created from the template. If today's note already exists, a new `## Session N` section is appended; nothing is overwritten.

```markdown
---
status: active
project: marty
type: daily
---
# 2026-10-01

## Index
- [[Grade a Practice Quiz]]: new Job note
- [[Switchboard]]: structured output added

## Session 1
- 9:10 AM: graded practice quiz 3, 17/20. Weak: PKI, incident response order.
- 10:40 AM: switchboard `--schema` added for all five lanes. Skeptic confirmed
  Gemini needs responseSchema, not response_format. Deployed, tests green.

### RESUME HERE (10:45 AM)
- Done: quiz 3 graded, switchboard schema live.
- In flight: none.
- Open question to Lukas: none.
- Next: build quiz 4 from the weak objectives.
```

## Checkpoints

A checkpoint is a single pass that leaves the vault true:

1. Update the note the work belongs to (an existing note first, a new one only if nothing fits).
2. Update that folder's index.
3. Append to today's daily note, ending with a **RESUME HERE** block: what is done, what is in flight with exact paths, any open question word for word, and the next action.
4. Scan the touched folder's index and the notes it cross-references for drift, and fix it.
5. Read each change back to verify it landed.

Checkpoints happen after every finished job and before any long read, so an automatic context compaction at any moment loses nothing. After a compaction, the session re-reads the root index and the newest RESUME HERE block and carries on.

## Renames

Obsidian repairs `[[links]]` only when a note is renamed inside the app. A rename done from the shell breaks every link to the old name, so renames happen in the app, or the agent finds and fixes every `[[old name]]` by hand in the same pass.
