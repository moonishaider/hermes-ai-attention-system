# Prompt 8 installed acceptance ledger

Date opened: 2026-08-23
Last reconciled: 2026-08-24 (Asia/Karachi)

This ledger mirrors the exact 48-item contract in `PROMPT_08_JARVIS_PRODUCT_HARDENING_GOAL.md`. Historical Prompt 7 acceptance is supporting context only and is never carried forward as a Prompt 8 pass.

Statuses: `Not tested`, `Automated pass`, `Installed pass`, `Visible pass`, `Blocked`, and `Failed`.

| # | Exact contract item | Status | Authoritative evidence / remaining proof |
|---:|---|---|---|
| 1 | Installed app build/runtime/plugin/grant/tool inventory are internally consistent | Installed pass | `/Applications/Jarvis.app` is running as bundle `com.moonishaider.jarvis` version `0.1.0`; deep strict signature verification passes; its binary embeds commit `af8ee1128ea472ed1a5316eae99b9cc443a70659` and has SHA-256 `ff9f483c1a3bfaaa78340c6710c245714fdc8219d13f3d9c48e3b9d18cd7260f`. The runtime plugin matches repository source, the Personal grant is exact-scope/refreshable, and all ten reviewed read-only integrations are registered. |
| 2 | Normal Personal Chat creates a simple event in the existing personal calendar and Undo succeeds | Not tested | Calendar capability is repaired and enabled in exact `auto-explicit` Personal mode; one normal-Chat create/Undo cycle in this installed build remains required. |
| 3 | Normal Personal Chat creates/opens an unsent Gmail draft | Not tested | Gmail-draft capability is repaired and enabled in exact `auto-explicit` Personal mode; one normal-Chat unsent-draft cycle in this installed build remains required. |
| 4 | Gmail send and work Google writes are absent | Automated pass | Renderer, native API, tool inventory, grant, and Action Firewall expose neither Gmail send nor Work Google writes; full negatives must be rerun at the final gate. |
| 5 | DLOA still works and can be revised in the same thread | Automated pass | Miami-time draft-only DLOA policy and canonical same-thread continuation are covered; one installed same-thread draft/revision remains required. |
| 6 | Typed prompt appears immediately as a user bubble | Automated pass | Canonical SessionDB user-message persistence and visible user-bubble rendering are covered; installed visual proof remains required. |
| 7 | Voice prompt appears identically after submission | Automated pass | Voice and typed submission use the same canonical message path; installed visual proof remains required. |
| 8 | Follow-ups remain in one thread | Automated pass | Owner prompt/final answer persistence is idempotent in the same canonical Hermes session; installed proof remains required. |
| 9 | Close/reopen restores the active thread | Automated pass | Active conversation ID is persisted immediately and restored from canonical SessionDB; installed lifecycle proof remains required. |
| 10 | Thread list/search/pin/archive/resume work | Automated pass | Jarvis-owned list/search/rename/pin/recoverable archive/restore controls are covered; foreign sessions remain filtered; installed proof remains required. |
| 11 | A 100-message thread remains usable | Automated pass | Frontend contract exercises a 100-message canonical thread; installed scrolling/responsiveness inspection remains required. |
| 12 | Composer auto-expands for a 5,000-character prompt | Automated pass | Frontend contract exercises 5,000 characters; installed visual proof remains required. |
| 13 | Sticky composer and scrolling work during a long answer | Automated pass | Layout and long-thread behavior are covered; installed visual proof remains required. |
| 14 | Technical tool details are collapsed by default | Automated pass | Progress/tool detail renders in a collapsed disclosure; installed visual proof remains required. |
| 15 | Sources render as compact useful cards | Automated pass | Evidence cards render source, date, freshness/confidence, and known/unknown status; installed visual proof remains required. |
| 16 | Normal navigation is Today, Chat, Inbox, Projects, Actions | Automated pass | Primary navigation contract is rendered and frontend-tested. |
| 17 | Build & Automate features are understandable and discoverable | Automated pass | Missions, Radars, Teach Jarvis, Focus, capability health, and Decisions are secondary/discoverable rather than competing primary destinations; installed UX proof remains required. |
| 18 | Context is inferred automatically and shown as a passive badge | Automated pass | Deterministic inference and passive badge are covered; Mixed/Unknown remain fail-closed; installed cross-context proof remains required. |
| 19 | Visual design passes a real screenshot review at common Mac window sizes with no overflow | Not tested | Requires installed-app screenshot inspection at common window sizes. |
| 20 | Natural speech auto-submits without Stop Listening | Not tested | Bounded silence finalization is implemented; owner-cadence acceptance remains required. |
| 21 | A mid-sentence pause does not submit prematurely | Automated pass | A 5.5-second bounded finalization window is covered; real cadence proof remains required. |
| 22 | A completed turn does not listen indefinitely | Automated pass | Bounded completion and ten-minute hard cap are covered; installed proof remains required. |
| 23 | Failed delivery retains transcript and Retry works | Automated pass | Retry/Edit/Discard retains the exact transcript and never submits before deliberate retry; installed visible proof remains required. |
| 24 | Spoken output is concise while full detail remains visible | Automated pass | Spoken projection excludes reasoning/tool traces while display retains the full final answer, progress, and citations; installed proof remains required. |
| 25 | Stop and barge-in work immediately with no replay | Not tested | Prompt 7 behavior is historical only; installed Prompt 8 proof remains required. |
| 26 | Calendar/Gmail requests use direct capabilities without repeated tool discovery | Automated pass | Native exact-capability router bypasses generic discovery; installed trace/timing proof remains required. |
| 27 | Routine chat does not query connectors | Automated pass | Direct route classification separates routine chat from source-backed retrieval; installed trace proof remains required. |
| 28 | Source progress is meaningful and cancellable | Automated pass | Source stages show checking/completed/unavailable/timed-out state and preserve cancellation; installed slow-task proof remains required. |
| 29 | System Health accurately reports every major capability | Automated pass | Runtime marker, build identity, connectors, model routes, budget, Personal action mode, grant freshness, and restrictions are sourced rather than synthesized; installed inspection remains required. |
| 30 | One safe Repair cycle fixes a deliberately simulated stale capability | Automated pass | Repair is restricted to reviewed local/backend/Personal-Google recovery families and cannot widen authority; installed simulated cycle remains required. |
| 31 | Today gives useful priorities, meetings, waiting-on items, blockers, forgotten commitments, and DLOA state | Automated pass | Today derives from immutable ledger evidence and reversible local state; bounded installed real-data usefulness proof remains required. |
| 32 | Inbox captures and closes one sourced commitment | Automated pass | Same-context source and completion-evidence rules are enforced; one installed lifecycle remains required. |
| 33 | One active Project Cockpit and Save My Place cycle work | Automated pass | Context-locked project snapshots/checkpoints preserve evidence and explicit next actions; installed lifecycle remains required. |
| 34 | One meeting lifecycle flow updates Inbox/Project state | Automated pass | Meeting follow-up accepts only authorized Zoom evidence in the active explicit context; installed lifecycle remains required. |
| 35 | One Mission, Radar, and Teach Jarvis workflow pass dry-run and activation | Automated pass | Each lifecycle is bounded, local/reviewable, context-scoped, and cannot self-modify protected authority; installed lifecycle remains required. |
| 36 | One Focus session produces a useful summary with no retained screenshot | Installed pass | The exact installed runtime completed a 30-minute Personal Focus start, pause, resume, one Jarvis app-metadata observation, and stop. The summary reported one observation, `com.moonishaider.jarvis`, Personal context, and zero retained screenshots; no external write occurred. Installed visible UI proof remains required. |
| 37 | One Decision Journal entry can be created and revisited | Automated pass | Decision creation requires same-context evidence and supports later explicit outcome recording; installed lifecycle remains required. |
| 38 | One Personal Administration Radar reports only a meaningful change or clean no-change state | Installed pass | The exact installed runtime evaluated the active Personal radar twice against twenty approved evidence records; both runs returned `materialChange=false`, `notification=none`, proving stable clean no-change behavior without external writes. Installed visible UI proof remains required. |
| 39 | Correct Chrome profile is visibly selected for a Personal and Inside Success navigation test | Not tested | Requires two installed visible navigation previews; no browser mutation is authorized. |
| 40 | Guided navigation can search/read without mutation | Automated pass | Fixed HTTPS/profile allowlists and read-only public retrieval are enforced; installed visible proof remains required. |
| 41 | A staged personal action requires the correct preview | Automated pass | Exact account/target/payload/permission/expiry/replay locks remain enforced; installed visible preview remains required. |
| 42 | No real company/client message, work-calendar change, purchase, payment, submission, destructive deletion, or unrestricted mode occurs | Installed pass | Installed product exposes no such authority; no prohibited action has occurred during Prompt 8 work. This must remain true through final acceptance. |
| 43 | Existing provenance, context, secret, budget, Action Firewall, destination lock, connector-negative, and guarded Git tests pass | Automated pass | Complete post-fix gate passes: marked-root preflight, safety controls/negatives, secret scan, configuration doctor, 102 Python tests, 20 frontend tests under pinned Node 24, production build, zero-vulnerability production npm audit, Rust fmt, warnings-denied Clippy, and eight Rust tests. Guarded publication remains pending. |
| 44 | Storage audit reports exact before sizes | Installed pass | Exact pre-cleanup measurements are recorded in `implementation/PROMPT_08_STORAGE_AUDIT.md`, including the repository, installed app, active runtime, shared Hermes footprint, build output, toolchains, backups, dependency tree, active runtime data, quarantine, Git, and idle RAM/CPU. |
| 45 | Cleanup manifest removes only allowlisted Jarvis-owned reproducible/obsolete artifacts | Blocked | Project safety policy forbids deletion through Python/Node/shell and requires project-local quarantine. A reviewed exact-manifest quarantine plan can be produced, but it will not be called deletion or counted as freed disk space. |
| 46 | Current app/runtime/database/secrets/history/memory and required rollbacks remain | Not tested | Must be verified after the policy-compliant storage step. |
| 47 | Jarvis launches and core health passes after cleanup | Not tested | Requires post-storage installed launch/health proof. |
| 48 | Exact freed space and retained footprint are recorded | Not tested | Final storage report required; safety-required quarantine may produce zero immediately freed bytes. |
