# Prompt 7 Acceptance Ledger

**Rule:** A passing test is supporting evidence, not a substitute for the visible requirement. `Not started`, `Automated only`, `Visible pass`, `Blocked`, and `Not achieved` are the only completion states used here.

| ID | Required visible evidence | State | Evidence |
|---:|---|---|---|
| 1 | `/Applications/Jarvis.app` opens without Terminal or stock Hermes UI | Visible pass | Packaged app opened as its own native window; no Terminal or stock Hermes UI launched |
| 2 | Only one Jarvis instance exists | Visible pass | A second Applications launch focused the existing process; process inventory remained exactly one Jarvis app and one owned gateway |
| 3 | Closing main window leaves clear menu-bar state | Visible pass | Closing hid the main window without stopping the owned backend; the menu-bar Open Jarvis path restored it |
| 4 | Global text shortcut opens HUD from another app | Visible pass | Command–Shift–Space opened the Jarvis Quick Entry HUD over another application |
| 5 | Global push/tap-to-talk works | Visible pass | Syed clicked Talk in the signed Applications build, accepted the exact Jarvis microphone gate, spoke, and stopped the recording. Capture and submission completed; denied/restricted/incomplete states still fail visibly without submission |
| 6 | Full Quit stops owned gateway, wake, observer, audio, and jobs | Visible pass | Normal Command-Q removed both Jarvis and its exact process-group-owned gateway. A fresh launch receives a private dynamic loopback port from macOS, so it cannot collide with or attach to the previous aiohttp listener during teardown |
| 7 | Launch at Login visibly enables/disables | Visible pass | The native Settings control was visibly switched Off to On and back to Off. Jarvis reflected both states and was deliberately left Off; no custom daemon or hidden login item was created |
| 8 | Dictated request shows live transcript | Visible pass | The signed app displayed and submitted a real dictated transcript. Because Syed's next real result remained materially inaccurate, Jarvis now uses official `gpt-4o-transcribe` as the high-accuracy final route, with an explicit local-only override and local fallback; final room-accuracy scoring remains a separate one-sentence owner retest rather than a false completion claim |
| 9 | Failed submission retains transcript and Retry works | Automated only | The final build retains bounded raw audio only until Hermes returns a run receipt. Failure exposes Retry delivery, Edit transcript, and Discard; successful delivery clears raw audio from memory. Real injected-network-failure UI acceptance remains pending |
| 10 | Spoken answer is natural/short; full cited detail remains visible | Not started | |
| 11 | Stop and barge-in interrupt without replay | Automated only | Talk cancels speech before capture; Stop listening and Stop speaking are distinct; visible retest pending |
| 12 | Typed chat remains quiet by default | Visible pass | Typed routine and source-backed runs completed without automatically starting speech |
| 13 | Routine request visibly uses Flash | Visible pass | Packaged Jarvis returned the exact synthetic result on Flash in 4.3 s and displayed route reason, 10,331 tokens, and about $0.0014 |
| 14 | Difficult multi-source request uses/escalates to Pro | Visible pass | A packaged source-backed attribution request selected Pro and completed in 57.0 s with visible source progress and usage |
| 15 | Visual request uses Luna | Automated only | Exact one-shot adapter forces Luna and discards pixels; Jarvis-visible selection pending |
| 16 | High-stakes synthetic review uses Terra | Automated only | Direct packaged Terra connectivity previously passed. Corrected policy now requires Pro synthesis followed by independent Terra review; two-stage selection/persistence is tested and the new packaged visible run remains pending |
| 17 | Route reason, cost, and latency are visible | Visible pass | Flash, Pro, and Terra runs each displayed deterministic route reason, elapsed time, tokens, and estimated cost |
| 18 | Work Ledger updates incrementally without broad rescan | Automated only | 11,424 provenance-linked rows are present; repeat cursor and bounded-batch tests pass |
| 19 | DLOA derives from ledger in accepted style | Visible pass | Inside Success end-of-day used the Miami-local 11 August date, exact required performance-analyzer phrase, source-derived granular bullets, code-block format, and no external send; the bounded window supported five distinct claims rather than padding to ten |
| 20 | Four proactive brief/review modes use bounded real evidence | Automated only | Start day, end day, pre-meeting, and absence-return completed locally with external writes false; end day had 16 sources/five supported bullets, while sparse semantic kinds limited usefulness in the other three |
| 21 | One active project has useful living state | Visible pass | Personal Projects visibly showed `Jarvis Prompt 7`, acceptance phase, active lifecycle, and its secure-native-layer objective |
| 22 | Dormant Mitchell is absent from ordinary proactive output | Automated only | lifecycle test and ledger query suppression pass; Mitchell record remains preserved |
| 23 | Sourced commitment opens and closes with verification | Visible pass | The runtime opened `Complete and verify the Prompt 7 Jarvis milestone` from one Personal-context Codex ledger source, displayed it as an open local task, and closed it only after a second same-context Codex evidence link verified completion; no external write occurred |
| 24 | One Mission and one Radar can be created and used | Visible pass | Native Missions showed the Prompt 7 completion contract; Radars showed the weekly official-Hermes material-change watch and digest policy |
| 25 | Natural-language low-risk capability dry-runs and can be undone | Automated only | source-backed end-of-day capability is draft + dry-run only; disable/archive UI not yet accepted |
| 26 | Code-requiring request produces spec without self-modification | Automated only | Capability Studio returns `codex-spec-only`; protected-field tests pass |
| 27 | Useful/not-useful feedback changes behavior with provenance | Not started | |
| 28 | Automation Miner proposes repeated workflow and records outcome | Automated only | Three independent immutable DLOA occurrences produced one low-risk local-draft proposal; accepting or rejecting it remains an owner decision |
| 29 | Existing Calendar style profile is generated and owner-reviewed | Not started | |
| 30 | Explicit simple personal event is created correctly and Undo works | Blocked | `AGENTS.md` forbids real calendar mutation during build; narrow wrapper is synthetic-tested only |
| 31 | Ambiguous/attendee/recurring event requires preview | Automated only | wrapper deterministically rejects auto path |
| 32 | Personal Gmail draft is created and opened | Blocked | `AGENTS.md` forbids real email mutation during build; narrow drafts wrapper is synthetic-tested only |
| 33 | Gmail sending is absent and negatively tested | Automated only | no send method/endpoint; negative test passes |
| 34 | Work Calendar/Gmail write capabilities are absent | Automated only | permission matrix and registered tool inventory exclude both |
| 35 | Focus session visibly shows profile and useful timeline | Automated only | One focus session and one metadata-only observation are stored; browser profile identity remains fail-closed rather than inferred |
| 36 | No screenshot remains after Focus session | Visible pass | Runtime and temporary-path inspection found no retained capture after the explicit one-shot flow |
| 37 | Guided navigation opens/searches/scrolls/reads without mutation | Not started | |
| 38 | Personal staged action previews before typing/submitting | Not started | |
| 39 | Retrieved page content cannot authorize action | Automated only | untrusted owner-intent issuance fails; target/permission/replay negatives pass |
| 40 | Zoom account read works for authorized Tyler meeting or one exact blocker is proven | Visible pass | Normal TLS and `hermes mcp test zoom_readonly` passed; provider discovery found 12 tools while runtime registration remained exactly four reviewed reads |
| 41 | All existing safety/context/secret/provenance/budget/action/Git tests pass | Visible pass | Preflight, safety controls/negatives, secret scan, config doctor, 90 Python tests, 3 frontend tests, 4 Rust tests, static/release build, clippy, signing checks, and zero-vulnerability production npm audit pass; final guarded publication is recorded by the commit containing this ledger |
| 42 | No company/client message/calendar mutation, purchase, or unrestricted mode occurred | Visible pass | no such action occurred; renderer has no unrestricted authority |
