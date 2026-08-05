# Prompt 6 Desktop Migration and Acceptance

**Date:** 6 August 2026

**Rollback source commit:** `2ae9512b2837fd4abd96a635375ba5d361bfa5ca`

**Rollback tag:** `prompt6-pre-desktop-upgrade-20260805`

## Release decision

The current official stable release was rechecked from the Hermes release and desktop documentation. Release `v2026.8.3`, published 3 August 2026 from signed commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb`, contains Hermes Agent 0.20.0 and the official Desktop, Quick Entry, real-time voice/barge-in, local wake-word, Journey/Memory Graph, learning, and desktop-plugin SDK capabilities required by Prompt 6. No newer stable release was selected.

The installed runtime reports `Hermes Agent v0.20.0 (2026.8.3)`. The official desktop package currently retains bundle version `0.17.0`; this is upstream packaging metadata and not the agent runtime version.

## Installation and preservation

The official DMG was downloaded and passed image, code-signature, Gatekeeper, and notarization checks. Its bundled setup script was not executed because review found project-forbidden destructive operations. Instead, the exact official source commit was built through its supported production packaging path after a pinned local dependency review. No remote script was piped into a shell, no local development server was started, and no custom daemon or launch agent was created.

The production dependency audit is clean. Electron is pinned to 40.10.6, Undici to patched 6.28.0/7.29.0 paths, and brace-expansion to 5.0.9. The locally built application is ad-hoc signed and passes strict local signature verification; unlike the downloaded bootstrap, this project-specific build is not Apple-notarized.

Recoverable backups exist under `~/.hermes/backups/`, including the pre-0.20 installation, configuration/SOUL/USER states, pre-schema database, pre-voice app, pre-stop-control app, and the final pre-acceptance configuration and SQLite backups. Both final backup databases pass `PRAGMA quick_check`. The previous 0.19.1 runtime is preserved under `~/.hermes/previous/`.

## Native product path

`/Applications/Hermes.app` is the primary interface. Command+Shift+Space opens native Quick Entry; Command+Shift+A opens the project Attention page. The project desktop plugin provides current context, safe status, tasks/open loops, one-shot screen understanding, response cancellation, a permanent Stop speaking control, learning navigation, and exact action-preview status. Its backend exposes only `GET /home`, `POST /tasks`, and `POST /screen`; it exposes no sender, executor, arbitrary path, browser, or computer-control endpoint.

The old Tk overlay and project launcher are no longer the normal interface. The fallback launcher's Finder working-directory defect was fixed by changing to the marked root before health and startup work. It remains diagnostic only.

## Voice and activation

- Quick Entry: Command+Shift+Space from another app, accepted visibly.
- Visible voice: native microphone control, accepted with macOS microphone permission.
- Wake phrase: local openWakeWord `hey_jarvis`, visible ear toggle, off by safe default on first configuration and currently enabled by Syed.
- Typed TTS: off, preventing long typed reports from being narrated.
- Microphone response projection: first one or two natural sentences, at most 45 words, with citations and structured evidence retained after `Details for screen:` for display only.
- Stop controls: native active-voice Stop, Attention Stop speaking, command-palette action, and configurable Control+Shift+S shortcut.
- Interruption: native Stop and the permanent Attention Stop speaking control both stop audio immediately while preserving the written reply. Spoken barge-in remains available in active voice conversation; the discoverable button/shortcut is the reliable fallback.
- Separate global talk shortcut: not added because the official SDK does not expose a clean supported voice-start action. The microphone and optional local wake phrase remain the supported paths.

The accepted calendar test was intentionally source-backed and took longer than a synthetic reply. Syed accepted the quality-preserving latency and confirmed the revised spoken answer was more natural. No answer-quality, citation, freshness, or context boundary was weakened for speed.

## Personalization and bounded learning

`SOUL.md` contains identity, calm confidence, concise answers, honest pushback, restrained dry humor, and serious-mode behavior for finance, tax, security, and professional output. `USER.md` contains only stable owner facts and preferences, including Syed/Moonis and Zoom Sid aliases. Inside Success, Mitchell, Personal, Mixed, and Unknown remain in the context registry rather than the personality files. Changing Slack, email, meeting, Codex, ChatGPT, and source evidence is not copied into either file.

Native memory and skill tools are enabled with both write-approval gates on. Notifications are visible; background review and the curator use DeepSeek V4 Flash. The curator is weekly, archival only, recoverable, non-consolidating, and forbidden from pruning bundled skills. Community-skill discovery remains unavailable. Runtime learning may save explicitly stated low-risk communication preferences and propose other local preferences/workflows, but security controls, credentials, OAuth scopes, repositories, model-budget limits, write destinations, external authority, and Hermes core cannot self-change. Syed created a real spoken-answer preference without Codex; Hermes stored it in Syed's stable profile. Because the native radial graph was not self-explanatory, Attention now adds a plain learned-item count, recent labels, and instructions while preserving the advanced graph and its inspect/edit controls.

## Preserved routing and boundaries

DeepSeek V4 Flash remains routine/default, DeepSeek V4 Pro remains difficult reasoning, GPT-5.6 Luna remains vision/screen, GPT-5.6 Terra remains rare review, and GPT-5.6 Sol remains Codex-builder only. Read-only connector allowlists remain intact. Generic Slack/email/calendar writes, unrestricted browser/computer control, checkout, payments, tax filing, destructive deletion, YOLO mode, and company/client write authority remain unavailable. The external-action kill switch remains on.

## Evidence to date

- Native Quick Entry opened successfully from another application, both before and after closing the main window.
- A source-backed project-resumption answer completed with citations and no external write.
- Real microphone, local STT, Flash, Edge TTS Ryan voice, and wake detection passed.
- The shorter voice projection passed a real calendar question and was accepted as more natural. A subsequent sky explanation proved the visible Stop control halts audio immediately while leaving screen detail intact.
- The visible wake switch persisted Off; repeated `Hey Jarvis` phrases produced no recording or response. Wake remains off at handoff.
- Native Attention completed one explicit Personal-context selected-area view after macOS permission restart; Luna returned a result and no transient screenshot remained.
- A real low-risk preference appeared as one learned item in Attention and in the native Memory Graph.
- Closing the main window preserved Quick Entry. Command+Q removed the app, backend, wake, and audio processes; a clean relaunch succeeded.
- Native typecheck, focused speech tests, production package, dependency audit, project configuration doctor, secret scan, safety controls, connector negatives, and 62 project tests pass.
- Sampled idle footprint was approximately 0.49 GiB RSS with wake off and approximately 0.61 GiB in an earlier settled wake-on sample; instantaneous CPU samples were about 5.9% off and 8.2% on. These are point samples, not a benchmark, and remain appropriate for the bounded 8 GB profile without a local LLM, Docker, Postgres, or development server.

## Final visible acceptance

Prompt 6 visible acceptance is complete: native open, Quick Entry, source-backed text, natural short voice, immediate Stop speaking, visible wake on/off with verified no-listening Off state, explicit selected-area Luna view with no retained image, native preference learning with a plain Attention summary, close/reopen, full quit with no residual processes, and clean relaunch all passed. Launch at Login remains off and was not requested.

## Rollback

Quit Hermes completely. Restore the dated pre-0.20 runtime/config/database/app backups appropriate to the failed layer, then check out commit `2ae9512` or tag `prompt6-pre-desktop-upgrade-20260805`. The project backup artifacts are outside Git and must never be published. Do not replace a newer database with an older backup without first preserving the newer file.
