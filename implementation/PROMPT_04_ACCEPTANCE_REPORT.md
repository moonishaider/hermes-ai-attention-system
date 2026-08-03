# Prompt 4 Real-World Acceptance Report

Checked: 4 August 2026. Private answers, source text, prompts, token values, and raw references were stored only in ignored owner-only runtime files. This report contains redacted counts, hashes, labels, latency, cost, and failure classes.

## Real-data results

The first nine-case run correctly stopped all cases when it discovered that the environment kill switch was not reflected in policy status. The policy bug was fixed so the kill switch blocks writes while permitting read-only operations. A subsequent nine-case run accepted one local Mitchell open-loop result; the other cases failed closed on insufficient current evidence, expired Google authorization, unavailable tool selection, or timeouts.

A focused run over 26 July–2 August accepted three of four cases after a robust parser recognized valid JSON following harmless model preambles:

| Case | Result | Sources | Citation/labels | Latency | Estimated cost |
|---|---|---|---|---:|---:|
| Cross-context Inside Success + Mitchell | Accepted | Codex and both Slack connections | 10/10 cited; 9 confirmed, 1 uncertain; contexts kept separate plus genuine unknown | 177.5 s | $0.01129 |
| Hermes project resumption | Accepted | Codex and personal GitHub | 10/10 cited; 7 confirmed, 2 inferred, 1 uncertain | 146.8 s | $0.01067 |
| Inside Success activity-report draft | Accepted, not sent | Company GitHub, Inside Success Slack, local draft | 4/4 cited; 3 confirmed, 1 uncertain; company context only | 173.3 s | $0.00845 |
| Mitchell focused live query | Timed out | Intended Slack + local evidence | No response at the bounded 180 s limit | 180.0 s | $0 |

A separate resource-accounted project-resumption acceptance passed again with 9/9 claims cited, 7 confirmed and 2 inferred, no reported leakage, 103.8 s latency, $0.00611 estimated model cost, and 175,472,640 bytes maximum resident set size (about 167.3 MiB). This is within the 8 GB Mac target, but live connector latency is too high for conversational daily use.

The strict suite initially did not accept “worked today,” the full Inside Success daily brief, personal upcoming obligations, context-switch handoff, or commitment/contradiction cases. Primary reasons were no current-date Codex evidence, expired Google tokens, empty local task/evidence windows, and connector timeout/tool-selection reliability. These were honest misses, not fabricated successes.

After owner-only backup and separate work Gmail, Drive, and Calendar reauthorization on 3 August, all three unchanged read-only metadata probes passed. Two focused real-data reruns then passed:

| Case | Result | Sources | Citation/labels | Latency | Estimated cost |
|---|---|---|---|---:|---:|
| Inside Success daily brief | Accepted | Codex, company GitHub, Inside Success Slack, work Gmail, work Calendar | 9/9 cited; 8 confirmed, 1 inferred; no reported leakage | 119.5 s | $0.01950 |
| What Syed worked on today | Accepted | Codex, company GitHub, Inside Success Slack, work Calendar | 6/6 cited; 5 confirmed, 1 uncertain; no reported leakage | 141.7 s | $0.01195 |

The second case preserved uncertainty and did not report other-person attribution. Private responses remain only in ignored owner-only acceptance files. Personal upcoming obligations were accepted later through the isolated Profile 1 direct-read fallback described below.

Zoom then passed a separate bounded usefulness case over 1–4 August. The assistant used only the filtered `zoom_readonly` connection, returned three source-backed recent work-meeting claims, cited 3/3 claims, labeled all three confirmed, kept the Inside Success context, reported no leakage, and completed in 65.5 seconds for an estimated $0.00523. The private answer and opaque provider references remain in ignored owner-only files; this report records only counts and outcomes.

Profile 1 then reauthorized personal Gmail, Drive, and Calendar with the exact reviewed read scopes. The initial provider probes were corrected because they had counted MCP error blocks as successful content. Official Google documentation and live calls established that the hosted Workspace MCP Developer Preview rejects the consumer account, while the same grants succeed against the standard Google APIs. Hermes now disables the three unsupported personal MCP servers and provides three bounded, host-locked GET-only project tools. After correcting date-only Calendar bounds to Asia/Karachi RFC 3339 values, the 1–10 August personal-obligations case passed with 6/6 claims cited, 5 confirmed and 1 inferred, mixed evidence explicitly retained as mixed, no reported leakage, 68.4 seconds latency, and $0.00308 estimated model cost.

The selected official ChatGPT export was 308.8 MB and used the current five-shard `conversations-000.json` through `-004.json` layout. Strict archive validation accepted only contiguous official shard names and bounded total conversation bytes. Preview found 458 conversations total and selected 47 from 1 March 2026 onward at 126,042,112 bytes maximum RSS. After exact approval, 47 records were imported; a rerun reported 0 inserted and 47 duplicates. All 47 records retained valid export provenance, 46 are inferred evidence and 1 is uncertain, and all remain honestly `unknown` pending semantic calibration. A hashed-query retrieval check found an imported record without printing source content.

## Classification calibration

Baseline Codex classification was 9,651 records: 4,910 Inside Success and 4,741 unknown (49.1244% unknown). Adding only the verified `new-casting-dashboard-main` workspace mapping reclassified 198 records to Inside Success. The new result is 5,108 Inside Success and 4,543 unknown (47.0728% unknown). Course-pipeline and Bayers records remain unknown because their contexts cannot be inferred safely.

The current archive is 187 files and roughly 6.9 GB; 64,000 lines are checkpointed. Current indexed timestamps do not prove activity on 2 August, so Hermes must not claim “today” from Codex alone.

## Representative model evaluation

All six bounded tasks scored 1.0 under the deterministic grounding/misattribution rubric:

| Route | Tasks | Median latency | Total estimated cost | Decision |
|---|---:|---:|---:|---|
| DeepSeek V4 Flash | 2 routine | 2.585 s | $0.0001596 | Retain as default |
| GPT-5.6 Luna | Same 2 routine | 2.301 s | $0.002239 | Keep for vision only; equal score at about 14x cost |
| DeepSeek V4 Pro | 1 difficult contradiction | 6.016 s | $0.00029754 | Retain for difficult reasoning |
| GPT-5.6 Terra | 1 high-stakes attribution review | 1.884 s | $0.0014575 | Retain for rare review |

This sample is intentionally small and cost-bounded. It supports retaining the approved router; it does not establish broad benchmark superiority. Live Hermes tool reliability is weaker than direct-model reliability because one Slack case timed out and several calls took 100–180 seconds.

## Public web/shopping acceptance

The public research smoke returned six cited search results for a harmless keyboard comparison and fetched 3,000 characters from one official manufacturer page. Results carried URL, retrieval time, content hash, source type, and untrusted-content status. Fetch blocked unsupported or unavailable pages without falling back to browser automation. Tests cover prompt-injection flags, script/style removal, secret redaction, credential-query rejection, and local/private-address rejection.

## Quality fixes made

- Made the action kill switch authoritative in runtime policy while preserving read-only use.
- Added exact MCP tool hints and bounded timeout handling to acceptance prompts.
- Made the result parser accept one valid case object after recording noncompliant preamble bytes.
- Added verified workspace provenance and Syed/Sid alias handling without forcing ambiguous context.
- Added credential-safe startup health with per-resource expiry warnings.
- Added a narrow public web search/fetch adapter and kept Hermes browser/computer toolsets disabled.

## Remaining acceptance gates

- The exact Inside Success destination is selected and locked. Sending remains deliberately unperformed; a fresh preview and exact payload approval are required if the user later requests a supervised test send.
- The requested Gemini Takeout archive has not arrived. Preview and importer work remain resumable when the ZIP is available.

## Closeout acceptance batch

The 4 August closeout strengthened the acceptance contract: every claim reference must now appear verbatim in exactly one source entry. Missing or duplicated references fail the case even if the model reports success. Prompts also cap each connection to one focused query plus one broadened query and prohibit identical retries. The runner supports at most two concurrent cases on the 8 GB Mac.

A focused Mitchell run passed in 120.8 seconds for an estimated $0.00607: 8/8 claims had exact resolved references across 10 sources, all labeled Mitchell, with no reported leakage. A final Inside Success retry timed out fail-closed at 180 seconds with no recorded API charge, so it was not retried.

For the two remaining multi-context requirements, a deterministic local composer consumed only strict-valid private inputs: the already accepted same-day Inside Success result was normalized by adding only its previously validated company Slack permalinks to the source table, and the new strict Mitchell result supplied the other context. Both context-switch handoff and commitment/contradiction cases then passed with 6/6 cited claims across 9 exact sources and both contexts. The contradiction result counts only explicit candidates in the bounded claims and deliberately makes no global “none exist” assertion. Composition made no connector call and performed no external action.

The DLOA v2 pipeline retained four confirmed claims and four validated Inside Success Slack permalinks, generated a destination-locked private preview, and omitted unresolved/uncertain claims. The preview expired safely. No sender is configured, no generic Slack send tool is exposed, and no message was sent.

An owner-only calibration packet was prepared with 12 bounded unknown records: six ChatGPT and six Codex samples. Applying decisions is owner-confirmed and hash-locked; no context labels were changed in this batch. Specialist acceptance passed seven controls covering persistent loading, context locks, publish/payment prohibitions, disabled serious mode, review routing, and isolated memory namespaces.

## Voice acceptance

The first supervised `/voice on` attempt found that earlier dependency checks targeted an unused `.venv` while the installed Hermes launcher runs `hermes-agent/venv`. The orchestrator now validates the actual runtime and the reviewed pinned voice packages are installed there.

A later deliberate sample passed the complete native path: live microphone capture, local faster-whisper transcription, DeepSeek Flash response, and audible Edge TTS. Syed compared the installed British male Thomas and Ryan voices and selected `en-GB-RyanNeural`; the prior Hermes configuration was preserved in timestamped owner-only backups before each change. Direct Ryan synthesis measured 2.04 seconds on the first request and 1.43 seconds on the repeat. A long sample stopped at a 1.5-second bound and a zero-volume playback completed without a residual player process.

The first continuous-mode attempt exposed `voice.auto_tts: false`: Hermes accepted speech but ordinary replies were silent, causing repeated recordings rather than a meaningful interruption test. After a new owner-only backup, automatic TTS was enabled and a single-turn speaker test became audible.

A realistic no-headphones run initially logged `Audio playback interrupted`, submitted the captured interjection as a new voice turn, and generated the requested shorter follow-up, but Syed's direct observation established that the original speech had not stopped immediately. Code review found the exact cause: Hermes 0.19.1 terminates macOS `afplay`, interprets its nonzero interrupted exit as a player failure, and falls through to `ffplay`, restarting the audio. The trusted project plugin now applies a process-local macOS guard that uses only `afplay` for the attempt and treats interruption as final; it does not edit the installed Hermes checkout or system audio settings.

The corrected no-headphones retest passed on 2026-08-02. Metadata-only telemetry recorded the first reply, `Audio playback interrupted` at 14:52:50, a 4.7-second captured correction, a second DeepSeek Flash turn, and no fallback replay or residual audio process. Syed confirmed Ryan stopped immediately and then answered the correction. Continuous mode correctly kept listening afterward; local Whisper misheard Syed's later “great” as “grade,” which produced a confusing extra response. This is an STT accuracy limitation, not a barge-in failure.

## Screen acceptance

On 2026-08-03 Syed selected one harmless Codex region through Apple's visible screenshot UI. GPT-5.6 Luna processed the authorized PNG successfully in 4.95 seconds, using 3,549 input and 256 output tokens at an estimated $0.0051. The private response was stored owner-only outside Git; metadata checks confirmed a visible-region description and no credential patterns. No continuous capture, Accessibility permission, or computer control was enabled.

macOS 26 ignored the requested destination when the full screenshot toolbar was used and saved the selected PNG to the Desktop. The exact new file was moved without inspection to owner-only Git-ignored quarantine, processed once through a fixed recovery path, and then moved recoverably to Trash. The generic recovery result incorrectly reported no retained pixels while that quarantine file still existed; this record supersedes that field. The one-time recovery option was removed from the permanent runner. The permanent adapter now forces selection-only mode, uses a random private temporary directory, and removes that directory before returning. After Syed explicitly confirmed the exact filename, Finder permanently deleted only that screenshot and showed the other six Trash items still present. No raw acceptance screenshot remains.

## Overlay acceptance

On 2026-08-03 the real foreground daily launcher displayed the startup transcript, safety status, context/source, and disabled-without-preview Approve control. Mute and Unmute updated only this launch's owner-only ephemeral voice-output state; the audit remained mode `0600`. The first signal-based Cancel attempt failed closed and was rejected as acceptance evidence. The corrected project-local Hermes 0.19.1 bridge then stopped an active DeepSeek Flash API call after about seven seconds through Hermes' native in-process interruption seam and did not queue another model turn. Dismiss hid the overlay, launcher exit removed the temporary control FIFOs/state, and no service or launch agent remained.
