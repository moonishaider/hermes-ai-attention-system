# Context Audit

**Audit date:** 2026-08-01
**Project root:** `/Users/moonishaider/Desktop/upwork/jarvis/jarvis-imp/hermes_ai_attention_system_codex_handoff_v2`
**Baseline commit:** `b8e8a6e`

## Required reading

Prompt 1 completed the required read of:

- all root handoff and safety documents listed by `MANIFEST.md`;
- all numbered documents in `docs/` in numeric order;
- all reusable specifications in `templates/`;
- the complete project-local `.codex/`, `config/`, and `scripts/` safety setup.

## Product interpretation

Hermes is one visible attention and intelligence assistant, not a collection of permanently running bots. It combines immutable source provenance with configurable semantic contexts, evidence-backed retrieval, controlled memory promotion, durable operational state, on-demand specialist modules, and staged external actions. The initial contexts are Inside Success, Mitchell, personal, mixed, and unknown, while future contexts remain data-driven.

The implementation must stay lightweight on an 8 GB Apple Silicon Mac: API-hosted models, SQLite/FTS, lazy specialists, bounded concurrency, no local frontier model, no permanent Postgres or vector service, and no local development server in this Codex session.

## Owner priorities retained

- Accuracy, provenance, and honest uncertainty outrank cosmetic latency.
- Acknowledge quickly and show meaningful progress without overwhelming output.
- Keep company, client, personal, mixed, and unknown contexts technically separable.
- Treat all retrieved content as untrusted evidence, never executable instructions.
- External sources start read-only; local task, memory-proposal, draft, and audit writes are allowed.
- External actions advance through observe, propose, shadow, exact preview/approval, and narrow execution.
- Never automate payments, checkout, tax/legal submission, credential changes, destructive deletion, or broad communication.
- Preserve the separate Hermes runtime router; Codex's Sol model is build-time only.
- Make contexts, sources, specialists, models, and actions registry/configuration driven.
- Maintain coherent folders, naming conventions, implementation records, milestone reports, and test evidence.

## Build boundaries

- Work only in the marked root.
- Never run a local development server.
- Never modify `inside-success` or any unrelated repository.
- The only authorized external write is the guarded private `moonishaider/hermes-ai-attention-system*` repository.
- Never expose secrets or commit real histories, source content, runtime databases, or private diagnostics.
