# Issues and deferred work

## Guarded repository script portability

`scripts/safe_create_private_repo.sh hermes-ai-attention-system` stopped before making a GitHub write because macOS Bash 3.2 rejects the Bash 4 lowercase expression `${LOGIN,,}`. No repository or remote was created. The script is a protected safety file and was not modified, bypassed, or replaced. Resolution requires a reviewed update to the protected script (for example, a portable case comparison) or an approved existing Bash 4+ runtime; installing a global shell is outside this implementation’s authority.

## Manual gates

- Install/review Hermes v0.19.1 and enable the project plugin.
- Enter provider keys outside Git and run low-cost route smoke tests.
- Select exact GitHub, Slack, Google, and Zoom accounts and approve only read scopes.
- Supply an official ChatGPT export if historical backfill is wanted.
- Decide whether to grant narrow macOS Screen Recording permission and add a reviewed capture adapter.
- Run real-data context and attention calibration, native voice acceptance, and backup/restore drill.

No local dev server, browser/computer control, real account mutation, live message/calendar/form action, OAuth flow, or macOS permission request was performed.
