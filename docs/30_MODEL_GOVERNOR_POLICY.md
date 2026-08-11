# Jarvis Model Governor Policy

**Checked:** 12 August 2026

The approved runtime routes remain:

| Route | Model | Automatic use |
|---|---|---|
| routine | DeepSeek V4 Flash | ordinary, low-risk text work |
| difficult | DeepSeek V4 Pro | cross-source, attribution-sensitive, contradictory, mixed-context, or explicitly source-backed synthesis |
| vision | GPT-5.6 Luna | only explicit one-shot image/screen interpretation |
| review | GPT-5.6 Terra | rare security, credential, tax, legal, financial, payment, irreversible, or production-incident review |

GPT-5.6 Sol is structurally absent from the runtime selector and remains Codex-builder-only.

Jarvis selects the route deterministically before run submission and passes the provider/model to Hermes’s authenticated run API. The UI displays the route and reason. When the run completes, it shows latency, token count, and a price-derived estimate using the checked configuration. Model-use records remain in the project database; prompts and responses are not copied into implementation logs.

The Python `ModelGovernor` remains the richer policy authority for source count, context count, contradictions, attribution ambiguity, evidence completeness, confidence, high stakes, optional-background budget stops, and independent Terra review. The current Rust front-controller covers the visible desktop route matrix. Automatic weak-answer re-review after a completed Flash response is not yet proven end to end and must not be claimed.
