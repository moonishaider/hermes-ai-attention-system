# System architecture

One Hermes assistant calls a narrow project plugin. The plugin invokes the local service facade; it does not expose a connector executor.

```text
Hermes UI / voice
  -> hermes-attention plugin (local tools only)
    -> deterministic policy + context router + specialist registry
      -> SQLite/FTS evidence, tasks, memory proposals, actions, audit, usage
    -> disabled-by-default source adapters
      -> GitHub / Slack / Google / Zoom / Codex / ChatGPT export
```

Every evidence item contains an immutable provenance record: source system, logical connection, native source ID and timestamp, retrieval time, account/workspace/container, author, URI, revision, permission reference, and source-specific metadata. A repeated evidence ID with changed provenance is rejected. Updated content retains the same immutable source coordinates while changing its content hash and revision evidence.

Context classification begins with provenance and deterministic rules. Multiple matching labels are retained and marked `mixed`; absent mappings become `unknown`. Any consequential action in either state fails closed. Browser profiles are metadata and never automatically launched.

The model router assigns DeepSeek V4 Flash to routine work, DeepSeek V4 Pro to difficult reasoning, GPT-5.6 Luna to explicit image/screen understanding, and rare GPT-5.6 Terra to high-stakes review. GPT-5.6 Sol is recorded as builder-only. Monthly usage is stored locally and optional work stops at the hard budget.

Action proposals include destination, payload, context, risk class A0-A4, browser profile, evidence IDs, expiry, idempotency key, and an exact preview hash. A2/A3 external execution is disabled, A4 is manual-only, and the Hermes tool surface has no executor. This implements shadow/preview behavior without pretending supervised live action has been authorized.

Specialists are persistent registry entries inside the same assistant. Each defines contexts, allowed and prohibited tools, memory namespace, model route, and serious-mode state. The template adds future specialists without another assistant or architectural rewrite.
