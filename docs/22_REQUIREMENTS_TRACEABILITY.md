# Requirements Traceability

Codex should replace `TBD` with code, test, and milestone references.

| Requirement group | Design source | Planned milestone | Code | Tests | Status |
|---|---|---:|---|---|---|
| PRD-001–010 | Docs 02, 04, 11, 13 | 1–3 | `src/hermes_attention/`, `.hermes/plugins/hermes-attention`, `hermes/` | `tests/test_core.py`, `tests/test_history_and_service.py` | Partial: working local assistant core; live voice/provider acceptance deferred |
| CTX-001–008 | Docs 05, 16 | 1–2 | `config/contexts.json`, `routing.py`, `policy.py` | context routing and fail-closed action tests | Implemented locally; calibration pending |
| SRC-001–012 | Docs 08, 09 | 2 | `history.py`, `github.py`, `config/integrations.json` | history, provenance, and negative tool-inventory tests | Partial: local/import routes work; OAuth connectors disabled |
| MEM-001–012 | Docs 06, 16 | 1–2 | `storage.py`, `extraction.py`, `attention.py` | immutable provenance, FTS, extraction, contradiction, queue tests | Implemented locally; real-data evaluation pending |
| SPC-001–008 | Docs 07 | 1 | `registry.py`, `specialists/`, `scripts/scaffold_specialist.py` | registry activation/context/disabled-state tests | Implemented |
| ATT-001–010 | Docs 13 | 3–4 | `attention.py`, `service.py`, `overlay.py` | queue, handoff, report draft/service tests | Partial: overlay and real workflow acceptance are manual |
| MOD-001–011 | Docs 10 | 0–5 | `config/models.json`, `models.py`, usage ledger in `storage.py` | route and hard-budget tests | Implemented as router/ledger; credentialed model calls pending |
| ACT-001–012 | Docs 12, 14 | 4–5 | `actions.py`, `policy.py`, `service.py`, plugin tool surface | hash, expiry policy, unknown/mixed, A4, shadow-only, no-executor tests | Preview/shadow implemented; executor intentionally deferred |
| OPS-001–010 | Docs 15, 17, 19, 20 | 0–6 | safety controls, doctor/scan/backup/test scripts, runbooks | preflight, safety verifier, unit suite, secret scan | Implemented locally; recovery drill/manual connector proof pending |
| GIT-001–009 | Docs 05, 08, 13, 16, 27 | 0–4 | `github.py`, two logical read-only configs | provenance and attempted-write rejection tests | Partial: code complete; live MCP OAuth/read smoke test pending |
| CDX-001–005 | Docs 15, 20, 28 | 0–1 | protected Codex controls, `history.py`, implementation records | preflight/safety verifier, incremental history test | Implemented; build session honored Sol/Medium/Full Access |

## Traceability rules

- Every implementation PR/commit should cite requirement IDs.
- Every acceptance test should cite requirement IDs.
- A requirement cannot be marked Complete without code/config and test evidence, unless it is explicitly a manual operational requirement with proof.
- Deferred requirements must state the reason and risk.
- A native Hermes feature still requires configuration/test evidence; “Hermes supports it” is not proof that this installation is safe or working.
