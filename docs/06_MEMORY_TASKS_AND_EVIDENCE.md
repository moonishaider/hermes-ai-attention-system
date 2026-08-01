# Memory, Tasks, and Evidence

## Four-layer model

### Identity and preferences

Small, always-relevant facts:

- name and aliases;
- concise response preference;
- desire for honest pushback;
- sarcasm preference;
- context definitions;
- budget and safety posture.

Use Hermes’s compact native user/memory mechanism after verifying current behavior.

### Trusted memory

Stable, confirmed knowledge:

- people and relationships;
- project decisions;
- durable preferences;
- approved workflows;
- specialist conclusions with source/date;
- known account/context mappings.

A trusted memory record must include provenance or a user confirmation.

### Operational state

- tasks;
- commitments;
- deadlines;
- blockers;
- decisions;
- unanswered questions;
- dependencies;
- next actions;
- project status;
- follow-up state.

Use Hermes Kanban/current equivalent where it meets requirements; extend with linked evidence and context metadata if needed.

### Evidence

Raw or normalized source material:

- Slack/email/Zoom;
- Codex/ChatGPT history;
- files;
- web research;
- screen snapshots explicitly captured.

Evidence may be stale, contradictory, mistaken, or malicious. It is not automatically trusted memory.

## Memory lifecycle

```text
source evidence
   -> extraction proposal
   -> confidence and contradiction checks
   -> user confirmation or trusted-rule validation
   -> durable memory
   -> later review/expiry/correction
```

Initial policy:

- automatic extraction may create **candidates**;
- no automatic promotion of sensitive or consequential facts;
- corrections are versioned, not silently overwritten;
- deleted source evidence must produce a revalidation flag for dependent memory.

## Retrieval strategy

Start with:

- live connector search for remote systems;
- SQLite FTS5 for imported/local histories;
- metadata filters before semantic/model reranking;
- bounded context windows;
- source diversity and freshness checks;
- short evidence summaries with links to original records.

Add embeddings/vector search only if a measured evaluation shows FTS/metadata/live search misses important results. If added, choose an API embedding or lightweight scheduled approach that does not burden the 8 GB Mac.

## Answer grounding

A meaningful factual answer should carry:

- answer;
- context;
- source title/system;
- source date;
- retrieval date;
- confirmed/inferred/uncertain status;
- confidence;
- contradictions or missing evidence.

When the system cannot support an answer, it should say so instead of filling the gap.

## Task/open-loop extraction

Candidates may come from:

- explicit “I will,” “please do,” or deadline language;
- meeting action items;
- unresolved Slack/email questions;
- Codex TODOs and incomplete work;
- user statements;
- calendar commitments.

A candidate enters Triage/Uncertainty unless confidence and policy permit automatic task creation.

## Contradictions

Do not resolve contradictions by selecting the newest statement blindly.

Store:

- claim A and evidence;
- claim B and evidence;
- dates;
- affected context/project;
- likely interpretation;
- requested user decision.

## Retention and minimization

- permit date-range and source filters;
- avoid copying entire remote accounts when live search suffices;
- redact secrets before indexing;
- allow delete/reindex by source, context, or time range;
- separate raw evidence retention from derived summaries;
- keep audit metadata even when content is removed, where appropriate.

## Performance targets

- common local task/memory lookup: near-instant;
- first response acknowledgement: immediate;
- source-backed cross-system answer: stream progress and return partial evidence before a long synthesis;
- no unbounded “load all history” operation at query time.
