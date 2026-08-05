# Hermes Post-Prompt-6 Product and Implementation Handoff

**Prepared:** 6 August 2026

**Purpose:** Self-contained factual handoff for Syed to upload to his ChatGPT browser and discuss the next product milestone.

**Repository:** Private `moonishaider/hermes-ai-attention-system`

**Local marked root:** `/Users/moonishaider/Desktop/upwork/jarvis/jarvis-imp/hermes_ai_attention_system_codex_handoff_v2`

**Operational code baseline before this handoff:** `main` at `732527e`

**Prompt 6 implementation commit:** `9ecbaec`
**Pre-Prompt-6 rollback:** `2ae9512`, tag `prompt6-pre-desktop-upgrade-20260805`

This document contains no API keys, OAuth tokens, imported conversation text, private Slack/email content, browser cookies, or runtime database records. It distinguishes implementation and automated verification from Syed's visible acceptance.

## 1. Product goal and why Prompt 6 existed

Hermes began as a source-backed attention and intelligence system with a strong local core, but its normal interface was Terminal-first and too technical. The original launcher, TUI, slash commands, and custom Tk overlay proved the backend but did not feel like a finished daily product.

Syed's desired product is one visible assistant that:

- opens like a normal Mac application;
- is reachable quickly from any application;
- supports natural text and voice without Terminal knowledge;
- keeps Inside Success, Mitchell, Personal, Mixed, and Unknown contexts separate;
- searches real connected evidence with citations and provenance;
- remembers explicit preferences and reusable low-risk workflows;
- can inspect one explicitly selected screen region without continuous monitoring;
- remains useful without receiving broad external authority;
- never silently sends messages, changes calendars, controls accounts, or widens permissions.

Prompt 6 was therefore a product realignment around official Hermes Desktop rather than another backend rebuild. Mobile was explicitly out of scope for that milestone.

## 2. Safety and operating boundaries that remain mandatory

- Never run a local development server on this Mac.
- Work only inside the marked project root.
- Preserve project hooks, command rules, `AGENTS.md`, the project marker, and guarded Git scripts.
- Do not use broad deletion, destructive cleanup, privilege escalation, history rewrites, or unrelated system changes.
- Direct Git pushes are forbidden; publication uses `scripts/safe_git_push.sh` only.
- The only authorized repository destination is the private personal repository under `moonishaider`. Never modify or push to Inside-Success.
- Do not expose credentials, tokens, imported histories, private source content, or runtime databases in Git or handoffs.
- Do not enable unrestricted computer/browser use, YOLO mode, generic Slack sending, company/client writes, payments, checkout, tax/legal submission, credential changes, permanent deletion, or arbitrary filesystem access.
- External sources begin read-only. Local task, draft, audit, and bounded memory-proposal writes are allowed.
- The external-action kill switch remains on.
- No persistent custom daemon, development server, launch agent, or hidden login item was created.
- Launch at Login remains off and requires a separate visible user decision.

## 3. Official Hermes upgrade and installation

Codex reverified the official stable Hermes release before migrating. Release `v2026.8.3`, published 3 August 2026, contains Hermes Agent 0.20.0 with the official Desktop app, Quick Entry, real-time voice/barge-in, local wake words, Journey/Memory Graph, learning, and the Desktop plugin SDK.

The installed runtime currently reports:

- Hermes Agent `v0.20.0 (2026.8.3)`;
- Python `3.11.4`;
- OpenAI SDK `2.24.0`;
- installation at `~/.hermes/hermes-agent`;
- primary application at `/Applications/Hermes.app`.

The official DMG was inspected for image integrity, signature, Gatekeeper, and notarization. Its bundled setup script was not blindly executed because review found operations forbidden by the project safety policy. The exact official source was instead built through its supported production packaging path after dependency review. No remote script was piped into a shell.

The locally project-adapted application is ad-hoc signed and passes strict local signature verification, but it is not Apple-notarized. The downloaded official bootstrap was notarized. The app bundle shows version `0.17.0` while the installed agent reports `0.20.0`; this is an upstream packaging-label mismatch, not a second Hermes runtime.

Backups exist under `~/.hermes/backups/`. The previous Hermes 0.19.1 runtime is preserved under `~/.hermes/previous/`. Database backups were made without overwriting the only copy and passed SQLite quick checks.

## 4. Current normal interface

The primary interface is now the official Hermes Desktop app. The Terminal launcher and old Tk overlay remain diagnostic fallbacks only.

Normal entry points:

- Open `Hermes` from Applications, Finder, Spotlight, or the Dock.
- Press `Command+Shift+Space` from another application for native Quick Entry.
- Press `Command+Shift+A` to open the project Attention page.
- Type in ordinary chat for a streamed answer.
- Click the native microphone beside the chat box for voice.
- Use the visible ear toggle for optional `Hey Jarvis` wake mode.

Quick Entry was visibly accepted from another app. It also remained available after closing the main window. Closing the window does not necessarily quit Hermes; `Command+Q` fully quits it. Full quit was tested and removed the app, backend, wake listener, and audio processes. Clean relaunch then passed.

The old Finder launcher bug was also fixed: it now changes to the marked project root and pins the Hermes Python 3.11 runtime. It remains a recovery tool, not the product's normal face.

## 5. Project-owned Desktop Attention surface

The project uses the official Desktop plugin SDK rather than a second standalone Mac app. The `Hermes Attention` page provides:

- current context selection;
- external-action kill-switch state;
- company/client-write availability state;
- monthly model-budget status;
- local tasks and open loops;
- local task creation with no external side effect;
- explicit `Look at selected area` screen understanding;
- `Cancel response`;
- `Stop speaking`;
- native Memory Graph navigation;
- a plain-language learning count and recent learned-item labels;
- the latest exact action-preview state, while execution remains unavailable from the plugin.

The Desktop backend exposes only three local routes:

- `GET /home`;
- `POST /tasks`;
- `POST /screen`.

It exposes no sender, action executor, arbitrary path, browser controller, generic computer control, or unrestricted filesystem endpoint.

## 6. Voice behavior and the complete acceptance history

The selected voice is the British male Edge TTS voice `en-GB-RyanNeural`, chosen by Syed after a side-by-side comparison.

The accepted voice path is:

1. native microphone control;
2. local faster-whisper speech recognition;
3. DeepSeek V4 Flash response/tool orchestration;
4. Edge TTS Ryan output;
5. written detail and citations left visible on screen.

Voice output was initially too much like a written AI essay. The Desktop response projection was changed so speech uses a direct natural prefix—normally one or two sentences and at most about 45 words—while structured detail remains visible after a `Details for screen:` boundary and is not read aloud.

Syed tested a real calendar question and judged the revised spoken reply more natural. He accepted the existing quality-preserving delay for a source-backed calendar lookup rather than reducing grounding quality for superficial speed.

Speech stopping was also tested:

- the native active-voice `Stop` control stopped immediately;
- the permanent Attention `Stop speaking` button stopped immediately;
- `Control+Shift+S` is available as a keyboard stop;
- stopping speech preserves the written answer;
- earlier Hermes 0.19.1 macOS replay behavior was fixed before the 0.20 migration;
- spoken barge-in exists during active voice conversation, but the visible Stop control is the dependable fallback.

Typed chat was designed to remain quiet while voice-originated turns speak. A current live configuration check after the latest app interaction found `voice.auto_tts: true`, even though the project merge sets it to false. This likely reflects a user/session voice toggle being persisted by Hermes Desktop. It has not yet been classified as a defect because recent use was inside voice conversation, but the next product review should decide whether Desktop must enforce “typed quiet, microphone spoken” more deterministically.

### First-use premature voice submission

After Prompt 6 acceptance, Syed found that a natural mid-sentence pause could be treated as the end of the turn. Diagnosis confirmed Hermes Desktop was using its official default of three seconds of continuous silence.

The supported configuration is now:

- `voice.silence_duration: 5.5` seconds;
- explicit `End` remains available when Syed finishes sooner;
- Stop controls remain unchanged.

The runtime configuration and plugin reload are verified. A real sentence with a roughly four-second mid-sentence pause still needs Syed's visible retest before this specific correction is marked accepted.

## 7. Wake phrase behavior

The optional wake phrase uses local openWakeWord:

- phrase: `Hey Jarvis`;
- local provider: `openwakeword`;
- visible ear/listening toggle;
- no separate hidden listener service;
- no microphone listening when the visible toggle is off;
- some additional CPU/RAM use when enabled.

Wake-off behavior was accepted earlier: repeated wake phrases caused no recording or response while the toggle was off. Syed later turned wake mode on during normal use. The current live configuration reports wake enabled. The project merge preserves a user's explicit visible choice instead of silently resetting it on every configuration run.

There is no separate supported global “start voice now” shortcut because the official Desktop plugin SDK does not expose a clean voice-start action. The supported choices remain the native microphone or optional wake phrase.

## 8. One-shot screen understanding

Screen understanding is explicit and one-time:

1. open Attention;
2. choose Inside Success, Mitchell, or Personal;
3. enter the reason if needed;
4. click `Look at selected area`;
5. select one region in Apple's visible selector.

The selected pixels are sent only to GPT-5.6 Luna for that request. The implementation does not continuously capture, retain the screenshot, click, type, use Accessibility permission, or expose computer control.

Syed granted macOS Screen Recording permission to Hermes, selected part of an Upwork conversation, and received a bounded description. Post-test checks found no retained screenshot in project or temporary runtime storage. This path is accepted.

## 9. Personalization and safe self-learning

Two concise personality/profile files are installed:

- `hermes/SOUL.md`: assistant identity, calm confidence, concise answers, honest pushback, restrained dry Jarvis-style humor, and serious literal behavior for finance, tax, security, legal, and professional output;
- `hermes/USER.md`: stable owner facts and preferences only, including Syed/Moonis identity, Zoom alias Sid, concise-response preference, context separation, Ryan voice preference, and interaction preferences.

Changing Slack, email, meeting, Codex, ChatGPT, project, or client evidence is not dumped into these files. Context classification remains in the context registry.

Hermes native memory, skills, Journey, Memory Graph, background review, and curator are enabled under a bounded policy:

May be learned locally when explicit and low risk:

- communication preferences;
- corrections to response behavior;
- recurring low-risk workflows;
- local templates;
- specialist procedures that use already-approved tools.

Must remain staged for review:

- uncertain personal facts;
- durable company/client facts;
- context-routing changes;
- new integrations or community skills;
- wider tools, filesystem reach, browser/computer access, or actions.

May never self-change:

- safety controls;
- credentials or OAuth scopes;
- protected repositories;
- model-budget limits;
- write destinations;
- external-action policy;
- Hermes core source;
- company/client permissions.

Syed told Hermes to remember that spoken answers should start directly and stay under two sentences. Hermes stored the preference without Codex. The native Memory Graph displayed it, but Syed found the radial graph confusing. Attention was therefore improved with a plain learned-item count and recent label; the graph remains an advanced inspect/edit view. Curator behavior is weekly, archival only, recoverable, non-consolidating, and forbidden from silently pruning bundled skills.

## 10. Contexts, relative dates, and the new Miami correction

Contexts remain data-driven and extensible:

- `inside-success`;
- `mitchell`;
- `personal`;
- `mixed`;
- `unknown`.

Syed's first real absence brief exposed an important time-zone problem. He asked after midnight in Pakistan what happened “yesterday” while absent from Inside Success. Hermes used the Pakistan civil date even though the company's workday was still on the previous date in Miami.

The context registry now assigns:

- Inside Success: `America/New_York` (Miami work clock);
- Personal: `Asia/Karachi`;
- Mitchell: currently `Asia/Karachi`;
- Mixed and Unknown: no single timezone; they fail closed and require per-source or explicit-date resolution.

The new `hermes_attention_context_time` tool resolves `today`, `yesterday`, or `tomorrow` into:

- context timezone;
- local date and time;
- local start/end;
- UTC start/end;
- Unix timestamps for connector searches;
- a bounded Slack and Calendar search recipe.

A deterministic boundary test proves that when it is 00:30 on 6 August in Karachi but still 5 August in Miami:

- Inside Success “yesterday” resolves to 4 August;
- Personal “yesterday” resolves to 5 August.

SOUL and USER guidance now require context-local date resolution before evidence retrieval and separate labeling for mixed-context windows. The automated correction passes; one real absence-brief retest remains.

## 11. The slow absence brief: observed cause and correction

The disappointing first-use absence summary was diagnosed from timing metadata without copying private Slack results into Git.

The failed user experience included:

- seven model calls;
- two redundant Slack channel-directory searches;
- a broad Slack result of 103,875 characters;
- many individual channel reads;
- roughly 59k input tokens by the later model turns;
- approximately two minutes for the useful response;
- the wrong relative-date window described above.

The provider/tool reads were generally quick—often under two seconds. The main latency came from poor orchestration and oversized evidence, not simply “the model being slow.”

The corrected first-pass strategy is:

- resolve the exact context-local date before searching;
- perform one bounded Slack search first;
- use exact start/end timestamps;
- return at most 20 results;
- request concise format;
- omit surrounding context initially;
- sort by time;
- do not enumerate all channels;
- read only threads/messages proven relevant by the bounded results;
- retain citations, provenance, freshness, confidence, and context separation.

This should materially reduce latency and cost without hiding evidence or using stale cache. It is intentionally recorded as implemented and loaded, not yet owner-accepted, until Syed retries the real request.

## 12. Runtime model routing

The accepted router remains unchanged:

| Route | Model | Purpose |
|---|---|---|
| Routine | DeepSeek V4 Flash | Normal conversation, extraction, routing, and tool orchestration |
| Difficult | DeepSeek V4 Pro | Hard reasoning after escalation |
| Vision | GPT-5.6 Luna | Explicit image and one-shot screen understanding |
| Review | GPT-5.6 Terra | Rare high-stakes independent review |
| Builder only | GPT-5.6 Sol | Codex implementation; not a Hermes runtime dependency |

The monthly budget thresholds remain approximately $25 warning, $40 soft, and $50 hard. A higher stretch budget requires an explicit policy change.

Flash and Luna tied on a tiny deterministic routine-quality sample. Luna was slightly faster in that sample but roughly 14 times more expensive, so Flash remained the routine default. No route was changed merely to appear faster.

## 13. Real connector state

All listed runtime connectors are logically separated and read-only.

### GitHub

- Personal `moonishaider` read-only connection: live and acceptance-tested.
- Company `Inside-Success` read-only connection: live and acceptance-tested.
- Separate fine-grained runtime credentials are used; the broad build-time credential is not reused.
- Owner/repository/ref/SHA/path/issue/PR/actor/timestamp provenance is retained.
- Create/update/merge/push/delete tools are excluded.
- Inside-Success is never modified.

### Slack

- Inside Success Slack read-only: live and used for accepted bounded retrieval.
- Mitchell Slack read-only: live and used for accepted open-loop/cross-context retrieval.
- Search/read tools only; send, channel creation, reactions, canvas/list mutation, and upload are excluded.
- No Slack message was sent during Prompt 6 or the first-use correction.

### Google work and personal

- Separate work and personal offline OAuth grants are active.
- Each grant contains only Gmail read-only, Drive read-only, Calendar-list read-only, and Calendar-events read-only.
- Automatic token refresh resolved the previous hourly-expiry frustration.
- The Google Workspace MCP Developer Preview did not support the combined grants reliably, so host-locked standard Google API GET-only tools are used.
- Gmail drafting/sending/labeling, Drive creation/upload/download, and Calendar create/update/delete/respond tools do not exist in the project runtime.

### Zoom

- Work Zoom read-only is active under the Inside Success account.
- Four reviewed meeting/recording read capabilities are exposed.
- Observed Zoom write capabilities remain filtered out.
- Bounded recent-meeting retrieval passed, but transcript depth still depends on provider recording/summary availability and sharing.

### Codex and ChatGPT history

- Codex history is incrementally ingested as read-only evidence with checkpoints and provenance.
- 187 source files and 64,500 lines were checkpointed at the recorded acceptance point.
- The official ChatGPT export importer selected and imported 47 conversations from 1 March 2026 onward from a five-shard export.
- A rerun detected all 47 as duplicates.
- Raw histories are evidence, not automatically trusted memory.
- No unsupported continuous personal ChatGPT-history synchronization is claimed.

### Gemini

- Syed requested an official Google Takeout export.
- Delivery is still pending.
- No importer was guessed before seeing the real archive schema.
- When it arrives, the archive must be previewed for schema, count, size, and date range before one explicit import confirmation.
- No continuous Gemini-history API is claimed.

### Public web and shopping research

- Read-only public search and guarded page fetch are live.
- URLs, dates, hashes, redaction, SSRF blocking, and prompt-injection treatment are implemented.
- No logged-in browser, cart, checkout, payment, or background browsing exists.

### Account, browser-profile, and secret separation

- Company Chrome / Profile 2 is the boundary for Inside Success Google and Zoom authorization.
- Profile 1 is the boundary for Personal Google and Mitchell/client authorization.
- Inside Success Slack and Mitchell Slack are separate logical connections and separate Slack apps.
- The Slack apps are installed only to provide the reviewed read surface. Hermes is not exposed as a general chat bot in company channels and has no generic send tool.
- The DeepSeek and OpenAI runtime keys are configured outside Git. The original values are not repeated in this handoff.
- GitHub runtime credentials are separate from the broader Codex/build credential.
- Google, Slack, and Zoom OAuth tokens are owner-only runtime state outside the repository.
- Secret scanning passed after every coherent publication milestone.

## 14. Existing source-backed capabilities

The following capabilities have working code and prior acceptance evidence:

- Inside Success attention brief;
- “What did I actually work on?” without attributing other people's work to Syed;
- Mitchell open loops, unanswered questions, and commitments;
- Personal obligations and tasks with work/client separation;
- cross-context search with source/context labels;
- context-switch handoff;
- project resumption from Codex/GitHub history;
- commitment and contradiction detection with original evidence references;
- unknown/mixed fail-closed behavior;
- source-backed daily activity-report drafting without sending;
- persistent specialist loading and context-scoped memory;
- serious-mode boundaries;
- public product research;
- natural short voice interaction;
- explicit one-shot screen understanding;
- bounded preference learning.

Past multi-source tasks can still take one to three minutes when they genuinely require many fresh sources. The new absence-brief correction targets avoidable orchestration cost; it does not promise every deep investigation will be instant.

## 15. Action posture and daily-report workflow

The initial Inside Success daily-report destination is locked to the selected `#sd-dloa-tyler` channel and Inside Success workspace. Six prior examples informed the format. The current preview contains only confirmed Syed claims backed by validated company Slack permalinks; uncertain claims were omitted.

The workflow remains preview-only:

- exact payload and destination lock;
- preview hash;
- expiry;
- idempotency/replay protection;
- broad-mention rejection;
- wrong-destination rejection;
- global kill switch;
- no generic Slack sender exposed to Hermes.

The previous preview expired safely. No real report was sent. Any future test send still requires explicit approval of that exact fresh payload.

Disabled-by-default preview hooks exist for later calendar creation, email drafts/sending, isolated downloads, and personal browser tasks, but they are not operational authority.

## 16. Resource observations

On the 8 GB Apple Silicon Mac, sampled Hermes Desktop footprint was approximately:

- 0.49 GiB RSS with wake off;
- 0.61 GiB in an earlier settled wake-on sample;
- approximately 5.9% instantaneous CPU off;
- approximately 8.2% instantaneous CPU on.

These are point samples, not a full benchmark. The design intentionally avoids local frontier LLMs, Docker, Postgres, a vector server, or a development server. Tool concurrency and source windows remain bounded.

## 17. Current live facts at handoff creation

- Git branch `main` is clean and matches `origin/main` at `732527e`.
- Hermes Desktop is running.
- Hermes Agent reports `v0.20.0 (2026.8.3)`.
- Routine model is DeepSeek V4 Flash.
- `voice.silence_duration` is 5.5 seconds.
- Wake is currently enabled through the visible user setting.
- Memory and skill write-approval gates are enabled.
- The latest plugin inventory loaded one additional project tool after the date correction.
- 64 project tests pass.
- Configuration doctor, secret scan, safety preflight, safety negatives, and guarded Git publication pass.
- No Slack/email message was sent, no calendar was changed, and no external-action authority was widened.

### Consolidated observations from Syed's visible use

- The native Desktop direction is materially better than the old Terminal/TUI path, but Syed expects a polished daily assistant rather than a technically impressive prototype.
- Quick Entry worked, but it is intentionally just a compact text box with a destination selector; it is an entry surface, not the full Attention dashboard.
- The original voice output sounded like written chatbot prose being read aloud. The short spoken-prefix projection improved this and was judged more natural.
- Long narrated responses are frustrating. Speech should remain short while full detail stays visible.
- The visible Stop control is understandable and reliable; spoken interruption is less discoverable and should not be the only stop mechanism.
- The Memory Graph is visually interesting but not self-explanatory. The plain Attention learning summary is the normal view; the graph should remain advanced.
- The screen selector initially caused confusion about clicking versus dragging, and macOS permission forced an app restart. After permission, selection and Luna interpretation worked correctly.
- The first real absence brief exposed that context time and retrieval strategy matter as much as model quality. Correctness and useful speed must be evaluated on actual daily questions, not only synthetic smokes.
- The Messaging page lists many platforms even when nothing is configured. In the current screenshot, WhatsApp was disabled, needed setup, and the messaging gateway was stopped. Seeing a platform in this page does not mean Hermes can already use it.

## 18. What is accepted, pending, deferred, or blocked

### Accepted

- Native app launch with no Terminal.
- Quick Entry from another application.
- Source-backed text response.
- Natural short microphone reply.
- Immediate visible Stop speaking.
- Wake on/off behavior, including verified silence while off.
- Explicit one-shot Luna screen selection with no retained image.
- Native preference learning and visible plain learning summary.
- Close/reopen/full-quit lifecycle.
- Read-only connectors and model routes.
- External-action boundaries.

### Implemented and loaded, awaiting one owner retest

- 5.5-second voice end-of-speech window.
- Miami-relative Inside Success date resolution.
- Bounded first-pass Inside Success absence-brief retrieval.

### Intentionally shadow-only or disabled

- Generic Slack sending.
- Inside Success report publishing without a fresh exact approval.
- Email/calendar/company/client writes.
- Broad browser/computer control.
- Payments, checkout, tax/legal submission, permission changes, deletion.
- Continuous screen capture.
- Launch at Login.

### Pending external artifact or optional judgment

- Gemini Takeout ZIP delivery and schema inspection.
- Optional 12-item semantic calibration of ambiguous historical context labels.

### Intentionally out of scope so far

- Mobile messaging/control.
- Continuous ChatGPT/Gemini account synchronization.

## 19. WhatsApp and iMessage/BlueBubbles evaluation

Hermes Desktop visibly offers WhatsApp and BlueBubbles, but neither was enabled.

### Bundled WhatsApp QR bridge

This is easiest to start but uses an unofficial personal-account bridge. It stores session credentials, can be logged out by protocol changes, and carries account-stability or ban risk. It should not be connected to Syed's primary WhatsApp number.

### Official WhatsApp Cloud

This is more stable and appropriate for production, but requires a dedicated business number, Meta Business configuration, a public HTTPS webhook, and management of the 24-hour messaging window. It is not the easiest personal remote-control path.

### BlueBubbles / iMessage

There is no direct official Apple iMessage bot API in this setup. Hermes integrates through BlueBubbles Server on the Mac. It is likely the most practical personal-phone route if Syed accepts:

- keeping the Mac on and reachable;
- running a persistent BlueBubbles server/gateway;
- granting that server access to Messages;
- using a strong local server password;
- restricting Hermes to Syed's exact identity/DM;
- disabling broad groups and unrestricted send behavior;
- understanding that full quit or Mac sleep makes the assistant unavailable.

This would introduce a persistent component and access to personal messages, so it must be a separate explicit milestone with threat review, allowlist tests, full-quit behavior, and rollback. It was not enabled merely because the UI displayed the option.

Current unbiased recommendation: do not use the unofficial bridge on the primary WhatsApp account. If Syed wants a near-term personal-phone path and accepts an always-on Mac, evaluate tightly scoped BlueBubbles first. If he wants maximum messaging stability and accepts heavier setup plus a separate number, use official WhatsApp Cloud.

## 20. Important implementation paths

- `START_HERE.md` — short nontechnical daily-use guide.
- `implementation/CURRENT_OPERATIONAL_STATE.md` — authoritative operational classification.
- `implementation/PROMPT_06_DESKTOP_MIGRATION_AND_ACCEPTANCE.md` — Prompt 6 migration and visible acceptance record.
- `implementation/FIRST_USE_DEFECT_FIXES_2026-08-06.md` — voice/date/latency diagnosis and correction.
- `implementation/ISSUES_AND_DEFERRED.md` — unresolved and intentionally deferred work.
- `implementation/REQUIREMENTS_STATUS.md` — requirement traceability summary.
- `hermes/SOUL.md` — assistant behavior/personality.
- `hermes/USER.md` — stable owner profile.
- `config/contexts.json` — context definitions and timezones.
- `config/models.json` — approved model routes and budgets.
- `config/integrations.json` — logical read-only connectors and exclusions.
- `.hermes/plugins/hermes-attention/` — project tool adapter and Desktop backend.
- `hermes/desktop-plugins/hermes-attention/plugin.js` — native Attention UI.
- `src/hermes_attention/context_time.py` — deterministic context-local dates and bounded search guidance.
- `scripts/configure_hermes_desktop_020.py` — safe idempotent config/SOUL/USER merge with backups.
- `patches/hermes-v2026.8.3-desktop-voice-response.patch` — exact native voice-response projection patch.

## 21. Commit history relevant to the current product

- `732527e` — first-use voice timing, context-local dates, and bounded absence-brief workflow.
- `9ecbaec` — official native Desktop migration and Prompt 6 acceptance.
- `2ae9512` — pre-upgrade product-realignment checkpoint and rollback tag.
- `347e8be` — Finder/Python fallback-launch correction.
- `fa71ff3` — initial safe first-use packaging.
- `116a86f` — durable Google offline refresh and hourly-expiry correction.
- `bf04f22` — Prompt 4 acceptance closeout.
- `817a87f` — destination-locked Inside Success report previews.
- `09717a6` — Zoom and personal context source activation.
- `f956ef3` / `19bc4a0` — screen privacy cleanup and accepted Luna screen view.
- `f009aa8` / `91acfbd` / `ed5f6af` — voice, automatic TTS, and macOS interruption acceptance before Desktop migration.

## 22. Rollback guidance

For only the latest first-use fixes, code can return to `9ecbaec`. Preserve any newer runtime database before restoring the matching owner-only pre-merge configuration/SOUL/USER backup under `~/.hermes/backups/`.

For the complete Prompt 6 migration, quit Hermes, preserve the current database, restore the appropriate dated app/runtime/config/database backups, and return to `2ae9512` or tag `prompt6-pre-desktop-upgrade-20260805`.

Never replace the only current database with an older backup, never remove backup directories broadly, and never use destructive Git history operations.

## 23. Highest-value next product discussions

The next planning conversation should prioritize product experience, not another broad architecture rewrite:

1. Validate the new 5.5-second voice pause and the Miami absence brief in one real session.
2. Decide whether voice completion should remain silence-based, add a visible/manual “done speaking” mode, or support both.
3. Decide the exact typed-versus-voice TTS contract because live `auto_tts` currently differs from the project merge default.
4. Review the bounded absence-brief result for usefulness, speed, attribution, and missing sources before introducing more optimization.
5. Decide whether mobile access is worth the persistent-service/message-access tradeoff; if yes, scope BlueBubbles as a separate personal-only milestone.
6. Decide whether wake mode should normally be on or off and whether the additional idle resource use is acceptable.
7. Keep Gemini import dormant until the official ZIP arrives.
8. Keep all external writes shadow-only unless Syed asks for one exact supervised action.

The current product is genuinely functional and considerably more usable than the Terminal-first version, but the first real absence-brief experience showed that “working” is not yet the same as consistently excellent. The next milestone should be evidence-led UX refinement around turn-taking, relative time, response speed, and mobile availability—without weakening provenance, context separation, or external-action safety.
