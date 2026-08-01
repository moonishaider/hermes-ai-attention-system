# Target Architecture

## Logical view

```text
Voice / Hermes Desktop / Overlay / Text
                  |
            Master Assistant
                  |
       +----------+-----------+
       | Context & Policy     |
       | Router               |
       +----------+-----------+
                  |
   +--------------+-------------------+
   |              |                   |
Specialist     Retrieval &         Action
Registry       Evidence            Proposal Queue
   |              |                   |
On-demand      Source adapters      Restricted executor
skills/workers |                   (disabled/limited first)
               |
  Slack x2 / Gmail x2 / Calendar / Zoom
  Codex history / ChatGPT backfill & relay
  documents / web / explicit screen
```

## Architectural components

### 1. Hermes runtime

Responsibilities:

- conversation loop;
- provider/model routing integration;
- MCP/native tool hosting;
- skills and delegation;
- voice and desktop UI;
- session behavior;
- built-in memory and Kanban where suitable.

Hermes is a shell/runtime, not the sole owner of all domain rules.

### 2. Context and policy router

A deterministic layer that:

- receives source metadata and user intent;
- assigns candidate semantic contexts;
- preserves immutable provenance;
- selects permitted tools and specialist modules;
- prevents outgoing cross-context leakage;
- chooses browser profile and action policy;
- marks uncertainty.

It should expose a simple policy API even if implemented as a Hermes plugin/tool.

### 3. Specialist registry

A configuration-driven index of persistent specialist modules. It resolves:

- specialist name and version;
- activation conditions;
- instructions/skill;
- allowed tools;
- memory namespace;
- source requirements;
- model routing;
- output schemas;
- evaluation suite;
- seriousness/personality policy.

### 4. Evidence and retrieval layer

Initial implementation should be lightweight:

- connector queries for live remote sources;
- embedded SQLite/FTS for local/imported Codex and ChatGPT evidence;
- normalized source references;
- incremental checkpoints;
- selective cached snippets/summaries;
- retrieval audit trail.

Do not build a separate distributed RAG platform unless measured need appears.

### 5. Memory and operational state

Use the most suitable verified Hermes-native memory/Kanban capabilities plus minimal supporting storage.

- identity/preferences;
- trusted facts/decisions;
- task/open-loop records;
- evidence links;
- memory proposals/approvals;
- contradiction records.

### 6. History bridge

- Codex local history/memory/session watcher;
- Git/repository activity summarizer;
- ChatGPT export importer with date filter;
- watched context inbox;
- optional explicit desktop capture adapter;
- deduplication and provenance.

### 7. Attention engine

Scheduled or on-demand processing that creates:

- attention queue;
- context handoff;
- project resumption snapshot;
- meeting prep;
- daily report draft;
- automation candidates;
- uncertainty triage.

It must obey cost budgets and source freshness rules.

### 8. Action proposal and executor

The master model generates a structured proposal. A deterministic executor validates:

- action type;
- policy/risk class;
- context;
- credential scope;
- exact target;
- preview hash;
- approval token;
- expiry;
- idempotency key.

The executor holds narrower credentials than the master and exposes only specific operations.

### 9. Overlay

A lightweight local desktop surface:

- live microphone transcript;
- acknowledgement/status;
- streamed response;
- sources/context;
- approval/cancel/mute/interruption controls.

### 10. Evaluation, audit, and cost control

- source-grounding tests;
- context-routing tests;
- action-safety tests;
- model comparison harness;
- latency and resource benchmarks;
- per-feature cost ledger;
- audit events and rollback points.

## Deployment topology

### Initial

Everything local except AI/voice APIs and remote SaaS connectors.

```text
MacBook:
  Hermes Desktop/runtime
  plugins/adapters
  SQLite state
  overlay
  browser/screen bridge
  local audit/logs

Cloud APIs:
  DeepSeek
  OpenAI
  STT/TTS provider
  Google/Slack/Zoom
  web search
```

### Optional later hybrid

A small CPU VPS may host scheduled ingestion, gateway/API, and lightweight queues. It must not receive browser cookies or computer-control authority. Local-only capabilities remain local.

## Replaceability

Define internal interfaces for:

- `SourceAdapter`
- `ContextClassifier`
- `EvidenceStore`
- `MemoryStore`
- `TaskStore`
- `SpecialistModule`
- `ModelRouter`
- `ActionExecutor`
- `OverlayEventBus`

Codex should map these concepts to verified Hermes extension points rather than creating abstraction for its own sake.

## GitHub source architecture update

Add two source adapters beneath the retrieval/evidence layer:

- `github_personal_readonly` for owner/account `moonishaider`;
- `github_inside_success_readonly` for owner/account `inside-success`.

Both use separate credentials and read-only policies but feed the same master assistant. GitHub owner/repository identity is immutable provenance; semantic context labels remain flexible. A dedicated private project repository under `moonishaider` stores this implementation, but build-time Codex write access to that repository must not be inherited by Hermes runtime.

