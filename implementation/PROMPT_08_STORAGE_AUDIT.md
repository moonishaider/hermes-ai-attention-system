# Prompt 8 Jarvis storage audit

Date opened: 2026-08-23

No Prompt 8 cleanup has occurred. Measurements below are the pre-change baseline.

| Exact path | Initial size | Classification |
|---|---:|---|
| Repository root | 13,267,536 KB | Active project plus many historical app/build backups; inspect after acceptance |
| `/Applications/Jarvis.app` | 6,036 KB | Active product; retain |
| `~/.hermes/jarvis-runtime` | 67,216 KB | Active runtime/database/code; retain |
| `~/.hermes` outside Jarvis runtime | Not yet finalized | Shared Hermes connectors, tokens, memory, skills; never broad-delete |

## Cleanup gate

Cleanup may begin only after the installed Prompt 8 app passes acceptance and a current rollback is retained. Candidates must be individually measured and proven redundant/reproducible. The cleanup operation must use an exact allowlist; current app/runtime/database/secrets/history/memory and unrelated computer files are prohibited targets.
