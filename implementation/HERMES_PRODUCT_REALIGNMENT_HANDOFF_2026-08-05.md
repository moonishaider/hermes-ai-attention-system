# Hermes Product Realignment Handoff for ChatGPT

**Prepared:** 5 August 2026  
**Audience:** Syed's ChatGPT conversation, for independent product analysis and a better next-phase plan  
**Project:** Hermes AI Attention & Intelligence System  
**Local project root:** `/Users/moonishaider/Desktop/upwork/jarvis/jarvis-imp/hermes_ai_attention_system_codex_handoff_v2`  
**Private GitHub repository:** `https://github.com/moonishaider/hermes-ai-attention-system`  
**Current branch:** `main`  
**Current implementation commit before this handoff:** `347e8be` (`Fix Finder launch Python runtime`)  

## Instructions to ChatGPT

Read this entire document before recommending anything. The purpose is not to celebrate the amount of infrastructure already built. The purpose is to reassess whether the product Syed can see and use matches the product he actually wanted.

Please produce an honest, unbiased product and implementation plan that:

1. preserves the accepted intelligence, evidence, connector, context-separation, model-routing, privacy, and action-safety work;
2. acknowledges that the current Terminal-first experience is not the desired final product;
3. makes first launch, ordinary text use, voice activation, one-shot screen use, status, cancellation, and quitting simple for a non-technical daily user;
4. explains what should happen to Hermes's native CLI/TUI, the custom overlay, and any proposed native macOS interface;
5. proposes a properly bounded personalization process for `SOUL.md`, user preferences, identity, memory, and contexts;
6. compares practical wake-word, push-to-talk, menu-bar, keyboard-shortcut, and always-available options, including their macOS permission and background-process implications;
7. treats mobile access as a separate product decision and compares iMessage/BlueBubbles, Telegram, WhatsApp, or another supported route without silently widening message authority;
8. distinguishes quick repairs from a genuine UX/product milestone;
9. provides acceptance criteria that measure visible usability rather than merely scripts, tests, or configuration;
10. ends with a strong implementation prompt Syed can give back to Codex after he approves the plan.

Do not assume the existing launch packaging is good enough merely because its automated tests pass. Do not recommend rebuilding the accepted core unless there is a concrete architectural reason. Do not expose or request secrets. Do not weaken the security boundaries described below.

## 1. What Syed originally wanted

Syed wanted one visible Hermes-based personal attention and intelligence assistant, closer in daily experience to a useful Jarvis than to a developer console. It should help him recover context and focus across:

- his Inside Success employment;
- the separate Mitchell Upwork client;
- personal projects and obligations;
- future clients, projects, sources, and specialist modules without creating another assistant.

The intended assistant should:

- understand what matters now;
- search authorized evidence across multiple sources;
- resume projects and context after interruptions;
- identify commitments, contradictions, tasks, unanswered questions, and open loops;
- distinguish Syed's work from other people's work;
- provide context-switch handoffs;
- remember stable facts carefully while retaining source provenance;
- perform current public-web and shopping research without checkout or logged-in browser control;
- accept text and natural voice interaction;
- show what it heard, what it is checking, and what it is answering;
- understand one explicitly selected screen region or window without continuous capture;
- preview consequential actions and require exact approval;
- remain extensible through registries, templates, adapters, and persistent specialist modules.

It was never intended to be a basic chatbot, a collection of permanently running autonomous employees, or an unrestricted computer-control agent.

## 2. Syed's current product feedback

The latest first-use attempt made clear that the implementation and Syed's intended product experience are not fully aligned.

Syed's direct feedback is:

- Double-clicking the launcher failed, so the promised first-use path did not work in the real Finder launch context.
- He does not want to operate the assistant through a basic-looking Hermes terminal/menu experience.
- Typing `/voice on` and then using `Control+B` feels too complex.
- He expected one simple wake command, one obvious keyboard combination, or one visible control.
- He expected the normal Hermes personalization/onboarding concepts, including `SOUL.md` and information about himself, to be handled clearly.
- He wants an honest plan for making the product genuinely simple rather than another infrastructure report.
- Mobile use may matter later. He mentioned iMessage as one possibility, but has not selected or authorized a mobile architecture.
- He explicitly requested that no implementation be started until he reviews a better plan produced with ChatGPT.

This feedback supersedes any earlier implication that Prompt 5 achieved final daily usability. The technical core remains valuable, but the visible user experience has not met the intended standard.

## 3. Current launch failure and exact diagnosis

The current project-local entry point is:

`Launch Hermes.command` → `scripts/launch_daily_hermes.sh` → Hermes 0.19.1

The real Finder launch printed the following sequence:

1. `Starting Hermes AI Attention...`
2. both Google accounts refreshed successfully and reported `ready-refreshable`;
3. the project health command raised `hermes_attention.config.ConfigurationError: marked Hermes project root not found`;
4. the wrapper correctly failed closed and reported that nothing was sent or changed externally.

The exact cause is visible in the current launcher:

- `scripts/launch_daily_hermes.sh` calculates the correct `ROOT` at line 4.
- It runs token refresh and project health before changing directories.
- It does not execute `cd "$ROOT"` until immediately before starting Hermes near the end of the script.
- `ProjectPaths.discover()` searches from `Path.cwd()` upward for `.hermes-ai-attention-project`.
- Finder/Terminal can start a `.command` file from a directory outside the marked project.
- Therefore the health process cannot discover the marker even though the script already knows the correct root.

This is a narrow, understood launch-order bug. The appropriate repair is to establish the verified root before any project Python command, or explicitly pass the root into every project command. The repair must be tested through a genuine Finder double-click and from an unrelated working directory.

The earlier Prompt 5 validation was incomplete: its minimal-environment check still used the project root as the command working directory, so it validated PATH isolation but did not reproduce Finder's working-directory behavior. Commit `347e8be` fixed the separate Apple Python 3.9 versus Hermes Python 3.11 PATH problem, but not this newly demonstrated root-discovery failure.

No implementation of this newly discovered repair has been performed as part of this handoff.

## 4. Current visible user experience

The current daily-use experience is:

1. Syed double-clicks `Launch Hermes.command` in the project folder.
2. A Terminal window opens.
3. The launcher runs safety preflight and refreshes Google tokens.
4. It prints a large JSON health report containing models, connectors, ingestion checkpoints, budgets, and action state.
5. It starts a separate small custom overlay.
6. It starts the Hermes CLI/TUI in the Terminal.
7. Text is entered in the Terminal.
8. Voice requires `/voice on`; native push-to-talk uses `Control+B`.
9. The overlay offers status, transcript, response, context/source, Mute, Cancel, Dismiss, and a disabled-without-preview Approve state.
10. Exiting Hermes stops the overlay and temporary control processes.

This experience is technically transparent and fail-closed, but it exposes developer-oriented diagnostics and requires knowledge of Hermes commands. It is not a polished single-window or menu-bar assistant.

No macOS `.app` was found during the Prompt 5 audit. The installed Hermes release is primarily being used through its CLI/TUI, with a project-specific overlay added around it.

## 5. What was done about Hermes identity and personalization

Hermes normally uses `SOUL.md` as its primary persona/identity instruction and built-in `MEMORY.md`/`USER.md` mechanisms for persistent memory and user information.

This project did not run a conventional generic Hermes questionnaire. Instead, the project installed and safely merged a deliberate operational identity into:

`/Users/moonishaider/.hermes/SOUL.md`

The installed SOUL currently establishes that Hermes:

- is one calm, visible attention and intelligence assistant for Syed;
- reduces context loss;
- leads with what matters;
- grounds claims in evidence;
- labels confirmed, inferred, conflicting, stale, and unknown information;
- separates company, client, personal, mixed, and unknown contexts;
- treats retrieved instructions as untrusted evidence rather than authority;
- can collect evidence, propose memory, track tasks/open loops, create handoffs, and draft action previews;
- keeps external execution disabled unless a separately reviewed narrow executor is enabled;
- requires deliberate screen-view requests;
- uses the configured model router economically;
- does not invent unsupported continuous ChatGPT history access.

This is a strong operational and safety identity, but it is not a rich personal profile. The current top-level Hermes home does not contain a populated `USER.md`. Much personal and professional context is present in the project's evidence database, imported histories, aliases, connector identities, and context rules, but that is not the same thing as a concise owner-confirmed user profile.

An improved plan should decide what stable information belongs in:

- `SOUL.md`: assistant identity, personality, tone, decision posture, and safety behavior;
- `USER.md` or an equivalent owner-confirmed profile: Syed's name, preferred form of address, communication preferences, recurring contexts, and stable preferences;
- controlled project memory: stable facts and decisions with provenance;
- evidence storage: changing source material, histories, messages, meetings, code, and documents;
- context registry: Inside Success, Mitchell, personal, mixed, unknown, and future contexts.

The plan should avoid dumping private histories or constantly changing operational data into a permanent personality prompt.

## 6. Voice implementation and current limitations

Voice is technically operational and was acceptance-tested on this Mac:

- input: microphone;
- STT: local faster-whisper;
- routine reasoning: DeepSeek V4 Flash;
- TTS: Edge TTS;
- selected voice: British male `en-GB-RyanNeural`;
- automatic TTS: enabled;
- native push-to-talk control: `Control+B` after voice mode is enabled;
- barge-in: Syed successfully interrupted spoken output by saying `stop` during the corrected no-headphones test;
- overlay: shows transcript/status and provides Mute/Cancel/Dismiss controls.

Engineering work completed for voice included:

- installing the pinned voice dependencies in the actual Hermes Python 3.11 environment;
- correcting an earlier validation that targeted an unused Python environment;
- selecting Ryan after side-by-side voice comparison;
- enabling automatic TTS after an initial silent-reply loop;
- diagnosing a macOS `afplay` interruption bug that caused fallback replay through `ffplay`;
- adding a project-local process-only guard so interrupted speech does not restart;
- validating voice without headphones;
- validating cancellation and no residual audio process.

Known limitation: local Whisper once heard “great” as “grade,” causing a confusing additional response. Short commands remain more error-prone than longer phrases.

Hermes 0.19.1 also contains a native local wake-word implementation:

- command: `/wake on`, `/wake off`, `/wake status`;
- default phrase/function: “Hey Hermes” through a free local wake-word provider;
- the enabled choice can persist in `config.yaml`;
- the current project configuration does not have wake word enabled;
- wake-word listening only helps while Hermes is running unless a persistent background architecture is separately chosen.

The current experience is too command-heavy for Syed. A better plan must decide among:

- automatically enabling a locally processed wake phrase when the app is open;
- one obvious in-app microphone control;
- a simpler application-scoped push-to-talk shortcut;
- a true global keyboard shortcut, including whether it needs an always-running menu-bar process or additional macOS permissions;
- an optional always-available mode, with explicit consent to the persistent-process and privacy tradeoffs.

It should not pretend that global wake or global keyboard activation can work while every Hermes process is stopped.

## 7. Implemented intelligence core that should normally be preserved

### Provenance and evidence

- Immutable source provenance records preserve source connection, owner/account, repository/workspace, ref/SHA/path, message/meeting/document identifiers, timestamps, hashes, and context labels.
- Retrieved content is treated as untrusted evidence and is scanned/redacted where appropriate.
- Claims can carry citations, dates, confidence, and confirmed/inferred/uncertain status.
- Unknown and mixed-context inputs fail closed rather than being forced into a convenient context.

### Context architecture

- Initial contexts are `inside-success`, `mitchell`, `personal`, `mixed`, and `unknown`.
- New clients, projects, tools, and sources are data/configuration entries rather than new assistant implementations.
- Deterministic classification uses safe provenance such as repository paths/remotes, workspace/account identities, known aliases, and configured context rules.
- One verified calibration reduced Codex-history unknown classification from about 49.12% to 47.07% by reclassifying 198 records; genuine ambiguity remained unknown.

### Retrieval, attention, and continuity

- SQLite and full-text search store derived evidence and checkpoints locally.
- The assistant can perform source-backed project resumption.
- It can generate Inside Success attention/work summaries without attributing other people's work to Syed.
- It can find Mitchell open loops, unanswered questions, and commitments.
- It can review personal obligations without leaking work/client data.
- It can create cross-context answers with source labeling.
- It can prepare context-switch handoffs.
- It can detect commitments and contradictions with original evidence references.
- It can draft an evidence-backed Inside Success daily activity report without sending it.

### Memory and tasks

- Raw imported history remains evidence, not trusted memory.
- Stable memory is promoted through scoped proposals rather than silently accepted.
- Memory, specialists, and tasks are context/namespace scoped.
- The system supports tasks, decisions, blockers, commitments, contradictions, open loops, uncertainty, and attention ranking.

### Specialists and extensibility

- Persistent specialists are registry/template-driven modules, not permanently running assistants.
- They load on demand with scoped instructions, tools, memory, and tests.
- Future specialists and client/source adapters should not require rewriting the high-level architecture.
- Serious mode and context restrictions are enforced and tested.

### Model routing

The approved direct-API runtime router remains:

- DeepSeek V4 Flash for routine conversation, extraction, routing, and ordinary orchestration;
- DeepSeek V4 Pro for difficult reasoning;
- GPT-5.6 Luna for vision and explicit screen understanding;
- rare GPT-5.6 Terra for high-stakes review;
- GPT-5.6 Sol for Codex building only, not as a routine Hermes dependency.

Representative tests were completed for all four runtime routes. Flash remained the routine default because it tied Luna on the small routine-quality sample while being materially cheaper.

### Cost and resources

- Soft/hard monthly budget controls and usage records exist.
- The illustrative model-cost scenario was approximately `$4.27/month`, though actual prices and usage can change.
- Edge TTS and local faster-whisper have no per-request API cost.
- Background concurrency is bounded for an 8 GB Apple Silicon Mac.
- A representative multi-source acceptance run measured about 167 MiB peak RSS.
- Some multi-connector tasks remain slow: representative cases have taken roughly one to three minutes.

## 8. Connected sources and their current status

All runtime connector credentials and tokens are outside Git in owner-only storage. No credential values belong in this handoff.

### GitHub

- Personal logical connection: `moonishaider`, read-only.
- Company logical connection: `Inside-Success`, separately bounded and read-only.
- Both use exact read-tool allowlists.
- Representative write tools were negatively tested as unavailable.
- The project private repository is under `moonishaider`.
- No code or changes were pushed to Inside Success.

### Slack

- Inside Success workspace: strict read-only connection.
- Mitchell workspace: separately isolated strict read-only connection.
- The Slack app experience remains off; the integrations are evidence sources, not bots added to channels for ordinary use.
- No generic Slack send tool is exposed to Hermes.
- No Slack message was sent during implementation or acceptance.
- The only contemplated future action is an exact-preview, destination-locked Inside Success daily report to `#sd-dloa-tyler`; it remains kill-switched and unsent.

### Google

- Work account: Gmail, Drive, and Calendar read-only through one exact-scope offline grant.
- Personal account: Gmail, Drive, and Calendar read-only through a separate exact-scope offline grant.
- Both grants refresh automatically and are stored outside Git.
- Work and personal data are context-isolated.
- The personal single-user app can show Google's unverified-app warning; formal public verification is intentionally deferred.
- No email draft/send, Drive write, or Calendar create/update/delete tool is enabled.

### Zoom

- Work Zoom is connected read-only to the Inside Success work account.
- The grant contains only the reviewed meeting/recording read scopes.
- Four reviewed read tools are exposed; observed provider write tools are filtered out.
- A bounded recent-meeting retrieval passed.

### Codex history

- Codex local history is incrementally ingested from 1 March 2026 onward using bounded batches and checkpoints.
- Tool output and hidden reasoning are excluded.
- Imported content is redacted and treated as evidence.
- Project-resumption retrieval passed.

### ChatGPT history

- The official ChatGPT export was previewed and imported after exact user approval.
- 47 conversations from 1 March 2026 onward were indexed.
- Reimport is idempotent; all 47 duplicates were recognized on rerun.
- No unsupported continuous ChatGPT account synchronization is claimed.
- An explicit context-relay workflow exists for important current conversations.

### Public web and shopping

- Read-only search/fetch with citations, content hashes, retrieval dates, and prompt-injection treatment is implemented.
- Logged-in browser control, cart changes, checkout, payments, and background browsing are disabled.

### Gemini

- Syed requested a Google Takeout export separately.
- No Gemini importer has been implemented because the official exported schema has not yet been inspected.
- This is explicitly deferred and is not part of the immediate usability repair.

## 9. Screen understanding

Explicit screen understanding is implemented as a one-shot local operation:

- Syed must deliberately request screen understanding.
- macOS shows the visible window/region selector.
- Only the selected pixels are sent to GPT-5.6 Luna.
- The capture is kept in memory and not retained automatically.
- No continuous capture is enabled.
- No Accessibility permission or unrestricted computer control is enabled.
- The result is redacted for credential-shaped output.
- Visible page instructions are treated as untrusted content.

A real supervised screen test passed. The current daily chat also exposes a reviewed one-shot screen tool, but the ideal UI for invoking it remains unresolved. The product should probably present a clear “Look at selected area” control rather than requiring Syed to remember a tool phrase or Terminal command.

## 10. Overlay and cancellation work

The custom overlay currently supports:

- current transcript;
- status/activity;
- streamed response text;
- context/source indicators;
- mute/unmute;
- cancellation of an active Hermes model turn;
- dismiss;
- approval state that remains disabled without an exact valid preview hash.

A real active Flash call was cancelled without queuing another model turn. Overlay state and audit data are owner-only and temporary where appropriate. The launcher tears down temporary FIFOs/state on exit.

The overlay is functionally useful but visually basic and separate from the Terminal. ChatGPT should decide whether it should:

- become the primary compact assistant window;
- be replaced by a native macOS app window/menu-bar interface;
- remain only as a transient status surface behind a better application shell.

## 11. External-action posture

The following remain intentionally disabled or shadow-only:

- generic Slack sending;
- email sending;
- calendar creation or modification;
- company/client writes;
- arbitrary downloads;
- logged-in personal browser tasks;
- unrestricted browser or computer control;
- payments, checkout, tax/legal submission, credential changes, destructive deletion, force pushes, or permission changes.

A narrow supervised-action executor exists outside the ordinary Hermes tool inventory. It enforces destination locks, exact payload hash, expiry, idempotency, context/risk policies, an audit record, and a global kill switch. It has not sent a real Slack message.

Any future mobile messaging interface would itself introduce outbound message delivery and a persistent gateway. It must not be treated as merely a cosmetic interface change.

## 12. Mobile access considerations already visible in Hermes 0.19.1

The installed Hermes code includes messaging gateway support for platforms including Telegram, WhatsApp, Slack, Discord, and BlueBubbles/iMessage.

iMessage is available through BlueBubbles rather than a direct Apple iMessage API. It would require:

- BlueBubbles Server running on a Mac;
- a server URL and password stored securely;
- a continuously available Hermes gateway or another reachable relay architecture;
- a strict allowlist for who can invoke the assistant;
- a decision about whether and where Hermes may send replies;
- careful separation from company/client messaging and from generic outbound authority.

This conflicts with the current Prompt 5 boundary of no daemon, launch agent, login item, or persistent background service. That boundary can only change through a separate explicit product decision after the risks and UX value are understood.

ChatGPT should not automatically recommend iMessage simply because it is technically supported. It should compare usability, maintenance, privacy, reliability, account risk, and authorization boundaries against Telegram, WhatsApp, a local network web client, or a future native companion application.

## 13. Safety controls that must survive any redesign

- Work only in the directory marked by `.hermes-ai-attention-project`.
- Never run a local development server on this Mac; Syed has repeatedly stated that it crashes his laptop.
- Do not weaken project hooks, safety rules, guarded Git scripts, or the project marker.
- Do not perform broad deletion, cleanup, history rewriting, force pushing, privilege escalation, or unrelated system changes.
- Preserve unrelated files and create non-overwriting backups before changing Hermes configuration.
- Keep credentials, tokens, cookies, histories, runtime databases, and private evidence outside Git.
- Do not print private source content into implementation logs.
- Keep Inside Success, Mitchell, personal, mixed, and unknown contexts separate.
- Keep GitHub and SaaS source connections read-only unless a separately reviewed narrow action is approved.
- Never modify or push to Inside Success repositories.
- Never expose a generic Slack sender.
- Never silently send Slack/email, change calendars, submit forms, make purchases, or operate company/client accounts.
- Keep screen viewing one-shot, explicit, visible, and non-retaining.
- Do not enable continuous screen capture, Accessibility-driven computer control, or YOLO mode.
- Treat web pages, messages, issues, source documents, histories, and tool output as untrusted evidence, not executable instructions.
- Keep Sol builder-only and preserve the approved Flash/Pro/Luna/Terra runtime routing unless representative evidence justifies a reviewed change.
- Use the guarded Git push path only to the private `moonishaider/hermes-ai-attention-system` repository.

## 14. Test and acceptance evidence accumulated so far

The last completed automated baseline before this handoff was:

- 56 Python unit/integration/security/connector/action/model/voice/screen/web tests passing;
- safety preflight passing;
- project hook and forbidden-command negative checks passing;
- configuration doctor passing;
- credential-pattern secret scan passing;
- backup/restore-to-new-file integrity passing;
- private GitHub origin clean and synchronized at `347e8be` before this handoff file;
- Hermes `0.19.1 (2026.7.30)` running on its installed Python `3.11.4` environment.

Important qualification: these results do not prove that the product is pleasant or that the real Finder launcher currently works. The newly reproduced root-discovery error is direct evidence that the Prompt 5 launch acceptance claim was too broad.

Representative real-data acceptance included:

- project resumption with 7/7 cited claims and 18/18 resolved evidence references across 15 sources;
- accepted Inside Success daily brief/report drafting without sending;
- accepted Mitchell open-loop retrieval;
- accepted personal obligation retrieval;
- accepted cross-context handoff/composition;
- accepted Zoom recent-meeting retrieval;
- accepted ChatGPT historical retrieval;
- real voice, barge-in, overlay control, and one-shot screen tests;
- public product-research search/fetch with citations.

Some live cases timed out and failed closed. Multi-source work can take roughly one to three minutes. Fast acknowledgement and meaningful progress reporting therefore remain important UX requirements.

## 15. Git and milestone history

The repository was initialized only at the marked project root and published privately through guarded scripts. Key commits are:

- `b8e8a6e` — baseline Hermes handoff package;
- `1761dee` — Hermes attention core and safe adapters;
- `97c41ae` — immutable source ingestion hardening;
- `d33ba5a` — rollback checkpoint before operational onboarding;
- `15614a0` — macOS Bash portability fix for guarded repository creation;
- `68854c3` — operational onboarding and safe runtime;
- `384e25f` / `f390c73` — live DeepSeek/OpenAI route validation;
- `45e4b6f` — separate read-only GitHub evidence connectors;
- `5f4f0f3` — strict Inside Success Slack read access;
- `d4f551d` — isolated Mitchell Slack read access;
- `8cb7f1a` — work Google read access;
- `cfae5e1` — personal Google read access;
- `015948b` — rollback checkpoint before real-world acceptance;
- `117c79e` — authoritative operational-state record;
- `00e0e3b` — bounded real-data acceptance harness;
- `731af5f` — safe daily-use evaluation and web research;
- `b87012c` / `f519a4e` / `ed5f6af` / `91acfbd` / `f009aa8` — voice runtime, Ryan selection, automatic TTS, macOS interruption fix, and accepted speaker barge-in;
- `19bc4a0` / `f956ef3` — accepted one-shot Luna viewing and screen privacy cleanup;
- `c05d816` — fail-closed overlay controls;
- `09717a6` — Zoom and personal source activation;
- `817a87f` — destination-locked daily-report previews;
- `bf04f22` — Prompt 4 acceptance closeout;
- `116a86f` — durable Google refresh-token resolution;
- `a9bcb61` — final Prompt 4 continuation handoff;
- `fa71ff3` — project-local first-use packaging and normal-chat screen tool;
- `347e8be` — explicit Hermes Python 3.11 runtime for Finder PATH compatibility.

Historical milestone documents should be preserved as evidence, but `implementation/CURRENT_OPERATIONAL_STATE.md` was intended as the current authority. It now needs a future correction because its “daily launch live and acceptance-tested” statement is contradicted by the 5 August real Finder failure.

## 16. Files ChatGPT should understand as current evidence

The most relevant files are:

- `implementation/CURRENT_OPERATIONAL_STATE.md` — dated operational truth through Prompt 4/early Prompt 5, now stale for the newly found Finder-root issue;
- `implementation/PROMPT_04_FINAL_HANDOFF_2026-08-04.md` — comprehensive Prompt 4 completion handoff;
- `implementation/PROMPT_04_ACCEPTANCE_REPORT.md` — real-data and UX acceptance details;
- `implementation/PROMPT_05_FIRST_USE_LAUNCH.md` — first-use packaging work and its earlier validation claim;
- `implementation/OPERATIONAL_TEST_EVIDENCE.md` — test and live-acceptance ledger;
- `implementation/ISSUES_AND_DEFERRED.md` — limitations and deferred items;
- `implementation/REQUIREMENTS_STATUS.md` — requirement-group status;
- `START_HERE.md` — current short user guide, which is not adequate while the real launcher fails and the UX remains Terminal-first;
- `scripts/launch_daily_hermes.sh` — canonical launcher containing the current root-order issue;
- `Launch Hermes.command` — Finder double-click wrapper;
- `hermes/SOUL.md` and `/Users/moonishaider/.hermes/SOUL.md` — project and installed assistant identity;
- `docs/11_VOICE_SCREEN_OVERLAY_AND_UX.md` — intended voice/screen/overlay experience;
- `AGENTS.md` and `docs/15_CODEX_EXECUTION_SAFETY.md` — mandatory project and safety boundaries.

## 17. Decisions ChatGPT should help Syed make

Please organize the next discussion around these decisions rather than immediately generating code:

1. **Primary daily interface:** native macOS window, menu-bar app, improved overlay, Hermes native UI, or another minimal shell around the accepted runtime.
2. **Terminal visibility:** completely hidden in normal use, available only under diagnostics, or retained as an advanced mode.
3. **Activation:** local wake phrase, application-scoped push-to-talk, global keyboard shortcut, visible microphone button, or a deliberate combination.
4. **Availability:** manual launch only versus an explicitly approved menu-bar/background mode.
5. **Personality:** how Jarvis-like the assistant should sound, when it should be serious, how concise it should be, and what stable facts belong in the owner profile.
6. **Progress UX:** what Syed should see immediately for slow multi-source tasks and how errors/freshness warnings should be summarized.
7. **Screen UX:** the simplest explicit one-shot selection flow that retains the accepted privacy boundary.
8. **Mobile:** whether it is valuable now or later, and which supported route has the best security/usability tradeoff.
9. **Packaging:** project-local unsigned app, a properly packaged local `.app`, or another verified option; include update and rollback behavior.
10. **Acceptance:** the exact real actions Syed must be able to perform without commands or technical knowledge before the milestone can be called complete.

## 18. Suggested standard for the next plan

A strong plan should probably separate at least three layers:

### Layer A — immediate correctness

- repair and genuinely verify Finder launch from outside the repository;
- stop exposing raw health JSON during normal startup;
- retain a diagnostic view for failures;
- update stale operational documentation honestly.

### Layer B — daily desktop product

- choose one coherent primary interface;
- make text, microphone, wake/push-to-talk, screen selection, sources, status, cancel, mute, and quit obvious;
- preserve the existing Hermes runtime and project plugin behind the interface;
- provide fast acknowledgement and source-by-source progress for slow tasks;
- validate with Syed performing representative tasks without Terminal instructions.

### Layer C — optional availability and mobile

- decide whether Hermes may run persistently;
- assess local privacy/resource implications of wake-word listening;
- choose a mobile transport only after defining the identity, allowlist, reply authority, context visibility, and failure/kill-switch model;
- keep mobile work out of the immediate desktop repair unless Syed deliberately combines the milestones.

ChatGPT is free to recommend a different structure, but it should explain why and must preserve the accepted safety and context boundaries.

## 19. What must not happen next

- Do not start implementation merely from reading this handoff.
- Do not treat the launcher bug as the entire product problem.
- Do not discard the accepted retrieval/connectors/context/action-safety core just because the UI is unsatisfactory.
- Do not declare the Terminal plus overlay to be a polished app.
- Do not enable a background service, login item, launch agent, or mobile gateway without an explicit decision.
- Do not enable wake-word listening without visible state and a clear off control.
- Do not add iMessage or another messaging platform without strict identity/allowlist and outbound-reply boundaries.
- Do not send any Slack/email/calendar/mobile message as a test without exact authorization.
- Do not ask Syed to perform routine terminal work.
- Do not expose private source content, histories, credentials, or account details in plans or implementation logs.

## 20. Requested output from ChatGPT

After reading this handoff, please give Syed:

1. a concise statement of the product you believe he actually wants;
2. an unbiased critique of the current implementation versus that product;
3. two or three viable UX architectures with tradeoffs, including which one you recommend and why;
4. a concrete voice/wake/keyboard interaction design;
5. a minimal personalization design for SOUL, user profile, memory, and context;
6. a separate recommendation for future mobile access;
7. a phased implementation and acceptance plan that reuses the existing safe core;
8. the few genuine product decisions Syed must make;
9. a final copy/paste Codex implementation prompt, but only after the plan is clear.

The desired outcome is not more documentation for its own sake. It is a plan for a visibly useful, pleasant, safe assistant that Syed can open and use without understanding Hermes internals or terminal commands.
