# Implementation Roadmap

The user does not want baby-step prompting. Codex should execute substantial safe work within each milestone, with a verification gate and Git rollback point.

## Milestone 0 — Compatibility and safe foundation

### Outcomes

- current Hermes stable release and extension surfaces verified;
- official model/provider/integration status verified;
- repository scaffold and test harness;
- safe Codex configuration guidance;
- threat model and architecture mapping;
- Hermes installed/configured from reviewed official sources under the Full Access safety protocol;
- one blank-slate/minimal Hermes profile;
- direct API provider configuration plan;
- no external source connection yet.

### Codex may do autonomously

- docs/audits;
- repository scaffold;
- interfaces;
- mocks;
- synthetic tests;
- configuration templates;
- CI/local test commands.

### Manual gate

- network/package provenance verification and logging;
- Hermes installation;
- API key entry.

## Milestone 1 — Intelligence core and extensibility

### Outcomes

- context/provenance model;
- policy router;
- specialist registry and generator;
- seed specialist modules;
- lightweight storage;
- task/open-loop structures;
- memory proposals;
- evidence citations;
- audit and usage ledger;
- fast acknowledgement/status event model;
- synthetic end-to-end test.

No real credentials required.

## Milestone 2 — History and connected evidence

### Outcomes

- read-only Codex history bridge;
- Git/project activity awareness;
- ChatGPT export importer with configurable start date;
- ChatGPT context inbox/relay;
- mocks/contracts for all connectors;
- first read-only Slack and Gmail connection after manual OAuth;
- second Slack/Gmail, Calendar, and Zoom connection;
- incremental checkpoints, source health, and provenance.

Codex should group connector work efficiently, but each OAuth/scopes screen is manually reviewed.

## Milestone 3 — Attention and desktop experience

### Outcomes

- attention queue;
- context-switch handoff;
- project resumption;
- commitment/open-loop extraction;
- contradiction detection;
- uncertainty inbox;
- meeting prep/follow-up;
- automation discovery and ROI tracking;
- voice benchmark/configuration;
- overlay;
- explicit screen capture;
- source-backed shopping research.

## Milestone 4 — Controlled actions

### Outcomes

- structured action proposal queue;
- shadow mode;
- browser profile mapping and display;
- personal A2 actions in supervised mode;
- daily Inside Success report generation;
- fixed-channel daily report publisher;
- draft/calendar action adapters where approved;
- idempotency, expiry, exact preview, kill switch;
- prompt-injection and context-leakage tests.

No A4 action is automated.

## Milestone 5 — Hardening and production trial

### Outcomes

- complete acceptance suite;
- model routing benchmark;
- cost/resource baseline;
- recovery and backup restore test;
- source freshness dashboard;
- security review;
- supervised real-world trial;
- user correction/feedback loop;
- rollout/rollback documentation.

## Milestone 6 — Optional hybrid/VPS

Only after evidence that laptop downtime causes missed value.

Possible remote responsibilities:

- scheduled read-only collection;
- task queue;
- gateway/API;
- health checks;
- encrypted backup.

Must not host:

- permanent GPU model;
- browser cookies;
- local screen/microphone;
- direct computer control;
- broad action executor without a separate security review.

## Milestone gate format

Every gate must report:

- requirements completed;
- tests and evidence;
- changed files;
- security posture;
- cost/resource measurements;
- unresolved risks;
- manual steps;
- rollback point;
- next milestone scope.


## Updated Stage 0 — two-prompt and GitHub preflight

- Prompt 1 reads the handoff, checks the environment/safety controls, verifies read access to `moonishaider` and `inside-success`, makes no file/system/external changes, acknowledges understanding, and stops.
- Prompt 2 creates Git baseline/rollback records, verifies current official capabilities, and begins implementation.
- Create or adopt the dedicated private personal project repository only in Prompt 2.
- Keep `inside-success` read-only throughout.
