# Prompt 4 Real-World Acceptance Report

Checked: 2 August 2026. Private answers, source text, prompts, token values, and raw references were stored only in ignored owner-only runtime files. This report contains redacted counts, hashes, labels, latency, cost, and failure classes.

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

The strict suite did not accept “worked today,” the full Inside Success daily brief, personal upcoming obligations, context-switch handoff, or commitment/contradiction cases. Primary reasons were no current-date Codex evidence, expired Google tokens, empty local task/evidence windows, and connector timeout/tool-selection reliability. These are honest misses, not fabricated successes.

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

- Reauthorize Google Developer Preview resources, then rerun work/personal acceptance and check the personal Gmail export notification.
- Retest immediate speaker-only barge-in with the macOS fallback guard, then complete one supervised visible-overlay mute/cancel pass. The microphone-to-spoken-reply loop and automatic TTS are accepted.
- Complete one explicit one-shot screen capture and Luna interpretation after Screen Recording permission.
- Authorize Zoom read-only and inspect its inventory now that normal TLS reaches the endpoint.
- Select the exact Inside Success Slack destination and approve one exact payload before any test send.
- Import the official ChatGPT ZIP after it arrives and is identified.

## Voice acceptance

The first supervised `/voice on` attempt found that earlier dependency checks targeted an unused `.venv` while the installed Hermes launcher runs `hermes-agent/venv`. The orchestrator now validates the actual runtime and the reviewed pinned voice packages are installed there.

A later deliberate sample passed the complete native path: live microphone capture, local faster-whisper transcription, DeepSeek Flash response, and audible Edge TTS. Syed compared the installed British male Thomas and Ryan voices and selected `en-GB-RyanNeural`; the prior Hermes configuration was preserved in timestamped owner-only backups before each change. Direct Ryan synthesis measured 2.04 seconds on the first request and 1.43 seconds on the repeat. A long sample stopped at a 1.5-second bound and a zero-volume playback completed without a residual player process.

The first continuous-mode attempt exposed `voice.auto_tts: false`: Hermes accepted speech but ordinary replies were silent, causing repeated recordings rather than a meaningful interruption test. After a new owner-only backup, automatic TTS was enabled and a single-turn speaker test became audible.

A realistic no-headphones run logged `Audio playback interrupted`, submitted the captured interjection as a new voice turn, and generated the requested shorter follow-up. Syed's direct observation nevertheless established that the original speech did not stop immediately. Code review found the exact cause: Hermes 0.19.1 terminates macOS `afplay`, interprets its nonzero interrupted exit as a player failure, and falls through to `ffplay`, restarting the audio. The trusted project plugin now applies a process-local macOS guard that uses only `afplay` for the attempt and treats interruption as final; it does not edit the installed Hermes checkout or system audio settings. The regression test passes, but live immediate-cut acceptance must be repeated before barge-in is marked operational.
