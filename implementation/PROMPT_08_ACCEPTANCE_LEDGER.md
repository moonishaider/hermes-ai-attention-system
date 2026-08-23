# Prompt 8 installed acceptance ledger

Date opened: 2026-08-23

Statuses: `Not tested`, `Automated pass`, `Installed pass`, `Visible pass`, `Blocked`, `Failed`.

| # | Contract item | Status | Evidence / next proof |
|---:|---|---|---|
| 1 | Installed app launches without Terminal | Not tested | Re-test packaged Prompt 8 app |
| 2 | Personal Calendar create and exact Undo from normal Chat | Not tested | Grant repaired; installed acceptance pending |
| 3 | Unsent personal Gmail draft from normal Chat | Not tested | Grant repaired; installed acceptance pending |
| 4 | Gmail send and work Google writes absent | Automated pass | Existing firewall/tool surface; rerun negatives |
| 5 | Canonical persistent conversations | Automated pass | Hermes SessionDB is canonical; governed review prompts are isolated while owner request/final answer persist idempotently |
| 6 | Recent conversation switcher | Automated pass | Jarvis-owned list/search/rename/pin/archive/restore controls covered; foreign sessions are filtered |
| 7 | Resume after quit/reopen | Automated pass | Active conversation is persisted immediately and restored; installed lifecycle proof remains pending |
| 8 | User messages visibly persist | Automated pass | User/assistant canonical messages and visible user bubbles covered by Python/frontend tests |
| 9 | Citations/progress persist with thread | Automated pass | Display metadata persists progress; evidence cards distinguish known and unknown freshness/confidence |
| 10 | Context inferred and visibly labeled | Automated pass | Deterministic inference and visible label covered; Mixed/Unknown remain fail-closed |
| 11 | Manual context correction is small and clear | Automated pass | Explicit-context correction is source-scoped, audited, and cannot target Mixed/Unknown |
| 12 | Context inference never widens Action Firewall | Automated pass | Route/context and personal-action negatives preserve exact account, target, scope, and owner-intent locks |
| 13 | Talk starts from visible control/shortcut | Not tested | Re-test packaged app |
| 14 | Natural end-of-speech waits for completed thought | Automated pass | 5.5-second bounded silence finalization and ten-minute cap covered; real owner cadence remains pending |
| 15 | Failed/partial transcript is recoverable | Automated pass | Retry/Edit/Discard retains the transcript and never submits before deliberate retry |
| 16 | Normal navigation is Today, Chat, Inbox, Projects, Actions | Automated pass | Primary navigation contract is rendered and frontend-tested |
| 17 | Advanced surfaces are secondary | Automated pass | Build & Automate surfaces are separate from the five daily destinations |
| 18 | One-time guided tour and useful empty states | Automated pass | Dismissible local tour and destination-specific empty states are frontend-covered |
| 19 | 100-message conversation remains usable | Automated pass | Frontend contract exercises a 100-message thread and 5,000-character message |
| 20 | Quick acknowledgement/status appears promptly | Not tested | Measure installed app |
| 21 | Slow task shows source-by-source progress | Automated pass | Live and persisted stage metadata render in collapsed progress details |
| 22 | Spoken response does not read tool traces | Automated pass | Spoken projection strips tool/reasoning detail while retaining useful final content |
| 23 | Display keeps full details/citations | Automated pass | Display projection preserves full answer, progress details, and evidence cards |
| 24 | Spoken stop/barge-in works | Not tested | Re-test packaged app |
| 25 | Simple local request starts capability in about 3 seconds | Not tested | Direct-router measurement pending |
| 26 | Calendar/Gmail bypass repeated tool discovery | Automated pass | Native exact-capability route is separate from generic discovery; installed timing trace remains pending |
| 27 | Capability health is truthful | Automated pass | Runtime marker, build identity, connector state, model routes, budget, and action modes are surfaced without synthetic success |
| 28 | Token freshness/reauthorization reason visible | Automated pass | Personal action status exposes exact scopes, refreshability, seconds remaining, and reauthorization-required state |
| 29 | Safe repair handles a bounded recoverable defect | Automated pass | Repairs are restricted to reviewed local/backend/personal-Google recovery families |
| 30 | Unsafe repair cannot widen scopes/tools | Automated pass | Repair and action negatives cannot add scopes, tools, destinations, or company/client authority |
| 31 | Today is source-backed and useful | Automated pass | Today derives from immutable ledger evidence and stores only reversible local attention state |
| 32 | Inbox separates waiting/blockers/commitments | Automated pass | Local task types, waiting owner, due date, lifecycle, and commitment completion evidence are enforced |
| 33 | Project Cockpit resumes with evidence and next actions | Automated pass | Context-locked project snapshots/checkpoints preserve evidence and explicit next steps |
| 34 | Meeting view preserves provenance/context | Automated pass | Meeting follow-up accepts only authorized Zoom evidence in the active explicit context |
| 35 | DLOA remains Miami-time and draft-only | Automated pass | Existing DLOA policy and no-Slack-send inventory remain covered; installed regression proof pending |
| 36 | Focus session yields summary without screenshot retention | Automated pass | 30/60/90/120-minute focus, pause/resume, metadata-only summary, and zero retained screenshots covered |
| 37 | Teach Jarvis stages bounded learning | Automated pass | Learning remains local/reviewable and cannot self-modify protected authority |
| 38 | Learned item is inspectable/reversible | Automated pass | Confirm/reject/supersede lifecycle is explicit and reversible in the reviewed local record |
| 39 | Radar alerts only on meaningful changes | Automated pass | Evidence fingerprint emits digest only on material change and remains context-scoped |
| 40 | Decision Journal stores evidence and later outcome | Automated pass | Decision creation requires same-context evidence and supports later explicit outcome recording |
| 41 | Staged action requires correct preview | Automated pass | Existing Action Firewall tests; rerun |
| 42 | Direct owner-request action remains account/target locked | Automated pass | Existing exact grant/firewall; rerun |
| 43 | Bulk/ambiguous/consequential writes fail closed | Automated pass | Existing parser/firewall; add Prompt 8 cases |
| 44 | Company/client writes and generic Slack sending absent | Automated pass | Existing negative tool inventory; rerun |
| 45 | Quit leaves no unintended gateway/audio/listener | Not tested | Installed lifecycle test pending |
| 46 | Security/secret/provenance/context tests pass | Automated pass | Pre-package gate: 101 Python, 20 frontend, production build, 8 Rust, fmt, warnings-denied Clippy, safety negatives, secret scan, doctor, npm audit |
| 47 | Working tree clean and guarded private push succeeds | Not tested | Final milestone |
| 48 | Exact freed space and retained footprint recorded | Not tested | Final storage milestone |
