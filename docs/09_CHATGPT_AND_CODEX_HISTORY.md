# ChatGPT and Codex History

## Goals

- know what Syed is currently building in Codex;
- recover decisions, blockers, completed work, and unfinished work;
- include important recent ChatGPT context without ingesting years of irrelevant history;
- avoid a daily manual export workflow;
- remain honest about unsupported APIs.

## Codex history bridge

Codex is the highest-priority history integration.

### Current structured synchronization

For current work, Hermes starts the installed official `codex app-server` only
for the duration of a synchronization and communicates over local stdio. The
client has a hard read allowlist containing only `thread/list` and the official
experimental `thread/turns/list`. The paginated turn method uses `itemsView:
summary`, which retains user/assistant conversation messages while excluding
large reasoning and tool payloads before they enter Hermes. No thread start,
resume, archive, delete, turn start, command execution, config write, or MCP
tool call is available through the bridge.

Hermes synchronizes automatically before DLOA/current-work/project-resumption
searches and before the daily-report draft tool. The Attention page also offers
**Sync latest Codex work**. Synchronization is incremental, bounded to recent
threads and turns, redacts secrets, preserves thread/turn/item provenance, and
stops the App Server child process when complete. A failure is reported rather
than treating stale evidence as current.

The experimental pagination status is a compatibility risk, not hidden. The
checkpointed local JSONL importer below remains the historical fallback. No
scheduled synchronization, permanent watcher, custom daemon, or network server
is enabled.

### Discovery

At runtime, discover the active `CODEX_HOME` rather than hard-coding one path. Verify current official paths and formats. Candidate sources may include:

- history JSONL;
- sessions;
- archived sessions;
- Codex memories;
- local task/run metadata;
- repositories and Git activity.

### Read-only guarantees

- open files read-only;
- never rewrite or “repair” Codex history;
- maintain bridge checkpoints in the project’s own state;
- use content hashes/session IDs for deduplication;
- tolerate format changes and malformed records;
- redact secrets before indexing;
- do not copy every token unless required.

### Derived records

Extract:

- repository/project;
- user goal;
- major decisions;
- changed files;
- commands/tests and outcomes;
- blockers/errors;
- TODOs/open loops;
- completion state;
- session/timestamp citation.

### Current-work awareness

Combine history with read-only Git evidence:

- active branch;
- uncommitted changes;
- recent commits;
- test status if available;
- project-specific handoff files.

Do not infer that an edited file means the task is complete.

## ChatGPT historical backfill

Use an official account export.

Configuration:

- default suggested start date: `2026-04-01`;
- Syed may change to May or another date;
- support selected-conversation allowlist/exclusion;
- preserve conversation ID/title/time;
- index only relevant content;
- do not make all raw conversation claims trusted memory.

The export may arrive asynchronously from OpenAI; this is a manual setup step outside Codex.

## Ongoing ChatGPT context

There is no assumed supported real-time personal ChatGPT history API.

### Supported primary path: context relay

Create a watched local `context-inbox/chatgpt/` or equivalent. Provide a reusable prompt/skill/action for ChatGPT Work/desktop that writes a structured context package after an important conversation:

- title;
- date;
- context labels;
- summary;
- decisions;
- commitments;
- unresolved questions;
- source conversation reference;
- optional selected excerpts;
- confidentiality/retention metadata.

The action should be one command/click, not a manual rewrite.

### Optional explicit desktop capture

Investigate a macOS/ChatGPT desktop adapter that captures the currently open conversation only after Syed explicitly invokes “sync this ChatGPT conversation.”

Rules:

- disabled by default;
- no background scraping;
- no hidden message sending;
- no reliance on undocumented cache schemas as permanent storage;
- clearly report when app UI changes break it;
- store evidence with `experimental` source status.

### Reconciliation

Periodically import a new official export and deduplicate against relayed/captured conversations.

## Search behavior

- metadata/context/date filtering first;
- retrieve concise relevant sections;
- cite conversation/session ID and date;
- surface stale/conflicting decisions;
- do not dump entire histories into the prompt.

## Promotion into memory/tasks

History evidence may generate candidates:

- confirmed decision;
- task/open loop;
- stable preference;
- project state;
- person/entity mapping.

Candidates require the memory policy defined in `docs/06_MEMORY_TASKS_AND_EVIDENCE.md`.

## Acceptance examples

- “What was I last doing in the X repository?”
- “What did I decide about Hermes model routing?”
- “Find the Codex session where I fixed the authentication issue.”
- “Resume the Mitchell automation project from where I stopped.”
- “This ChatGPT chat supersedes an older decision; show both.”
