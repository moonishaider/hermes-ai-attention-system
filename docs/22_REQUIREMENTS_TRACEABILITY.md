# Requirements Traceability

Codex should replace `TBD` with code, test, and milestone references.

| Requirement group | Design source | Planned milestone | Code | Tests | Status |
|---|---|---:|---|---|---|
| PRD-001–010 | Docs 02, 04, 11, 13 | 1–3 | TBD | TBD | Planned |
| CTX-001–008 | Docs 05, 16 | 1–2 | TBD | TBD | Planned |
| SRC-001–012 | Docs 08, 09 | 2 | TBD | TBD | Planned |
| MEM-001–012 | Docs 06, 16 | 1–2 | TBD | TBD | Planned |
| SPC-001–008 | Docs 07 | 1 | TBD | TBD | Planned |
| ATT-001–010 | Docs 13 | 3–4 | TBD | TBD | Planned |
| MOD-001–011 | Docs 10 | 0–5 | TBD | TBD | Planned |
| ACT-001–012 | Docs 12, 14 | 4–5 | TBD | TBD | Planned |
| OPS-001–010 | Docs 15, 17, 19, 20 | 0–6 | TBD | TBD | Planned |
| GIT-001–009 | Docs 05, 08, 13, 16, 27 | 0–4 | TBD | TBD | Planned |
| CDX-001–005 | Docs 15, 20, 28 | 0–1 | TBD | TBD | Planned |

## Traceability rules

- Every implementation PR/commit should cite requirement IDs.
- Every acceptance test should cite requirement IDs.
- A requirement cannot be marked Complete without code/config and test evidence, unless it is explicitly a manual operational requirement with proof.
- Deferred requirements must state the reason and risk.
- A native Hermes feature still requires configuration/test evidence; “Hermes supports it” is not proof that this installation is safe or working.
