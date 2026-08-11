# Requirements Traceability

Codex should replace `TBD` with code, test, and milestone references.

| Requirement group | Design source | Planned milestone | Code | Tests | Status |
|---|---|---:|---|---|---|
| PRD-001–010 | Docs 02, 04, 11, 13, 29 | 1–3, Prompt 7 | `src/hermes_attention/`, `.hermes/plugins/hermes-attention`, `jarvis/` | core/history/operational/Prompt 6/Prompt 7 suites plus visible acceptance ledger | Native Jarvis operational; narrow microphone/Luna/profile checks remain |
| CTX-001–008 | Docs 05, 16, 29, 31 | 1–2, Prompt 7 | `config/contexts.json`, `routing.py`, `policy.py`, `work_ledger.py` | context routing, ledger, lifecycle, and fail-closed action tests | Implemented; Mitchell preserved as dormant |
| SRC-001–012 | Docs 08, 09, 31 | 2, Prompt 7 | `history.py`, `github.py`, `google_direct.py`, `work_ledger.py`, integration config | history, provenance, ledger, live read-only connector, and negative inventory tests | Operational for GitHub, Slack, Google, Zoom, Codex, ChatGPT/Gemini imports, and public web |
| MEM-001–012 | Docs 06, 16, 31 | 1–2, Prompt 7 | `storage.py`, `extraction.py`, `work_ledger.py`, `projects.py` | immutable provenance, context-before-limit FTS, ledger, contradiction, queue tests | Implemented with 11,424-row real-data projection and uncertainty preserved |
| SPC-001–008 | Docs 07 | 1 | `registry.py`, `specialists/`, `scripts/scaffold_specialist.py` | registry activation/context/disabled-state tests | Implemented |
| ATT-001–010 | Docs 13, 29 | 3–4, Prompt 7 | `attention.py`, `service.py`, Jarvis chat/Attention surfaces | queue, handoff, report, voice/screen policy, packaged visible checks | Operational; real Jarvis microphone and Jarvis-originated Luna remain supervised checks |
| MOD-001–011 | Docs 10, 30 | 0–5, Prompt 7 | `config/models.json`, `models.py`, `model_governor.py`, Jarvis adapter | route matrix, budget, provider and packaged visible delegation | Flash/Pro/Terra visibly passed; Luna forced for pixels; Sol impossible at runtime |
| ACT-001–012 | Docs 12, 14, 33 | 4–5, Prompt 7 | `actions.py`, `action_firewall.py`, `personal_google_actions.py` | owner origin, permission drift, replay/crash, endpoint, target and send-absence negatives | Generalized fail-closed firewall implemented; protected live mutations remain gated |
| OPS-001–010 | Docs 15, 17, 19, 20, 34 | 0–6, Prompt 7 | safety controls, Jarvis package, doctor/scan/backup/test scripts, runbooks | preflight, safety verifier, 86 Python/1 frontend/3 Rust tests, clippy, secret scan, release build | Operational private local build; ad-hoc signed and rollback-tested |
| GIT-001–009 | Docs 05, 08, 13, 16, 27 | 0–4 | `github.py`, two logical read-only configs, guarded scripts | provenance, attempted-write rejection, live MCP reads, guarded publication | Operational for separate personal/company reads; Inside Success writes impossible |
| CDX-001–005 | Docs 15, 20, 28 | 0–1 | protected Codex controls, `history.py`, implementation records | preflight/safety verifier, incremental history test | Implemented; build session honored Sol/Medium/Full Access |

## Traceability rules

- Every implementation PR/commit should cite requirement IDs.
- Every acceptance test should cite requirement IDs.
- A requirement cannot be marked Complete without code/config and test evidence, unless it is explicitly a manual operational requirement with proof.
- Deferred requirements must state the reason and risk.
- A native Hermes feature still requires configuration/test evidence; “Hermes supports it” is not proof that this installation is safe or working.
