# Voice Input Reliability and Personality Update

**Date:** 6 August 2026
**Scope:** Hermes Desktop long-input reliability and `SOUL.md` personality refinement
**External actions:** No message, calendar event, browser action, company/client write, or permission change was performed.

## Reported problems

1. A long spoken request could disappear, forcing Syed to repeat it.
2. Hermes needed more charisma and occasional light sarcasm without reducing work quality.

## Verified causes

The native continuous voice path used two hard-coded limits independent of the reviewed project settings:

- 1.25 seconds of silence automatically closed the current turn, which is too short for a natural mid-sentence pause.
- 60 seconds automatically closed a long turn, even though ordinary dictation supported a longer bounded limit.

When transcription returned empty or raised a temporary error, the captured audio was discarded after the first attempt. No recent backend crash was found; these native UI behaviors were sufficient to explain the reported failure mode.

## Implemented correction

- Continuous voice now waits 5.5 seconds of silence before closing a turn.
- Both continuous voice and push-to-talk use a configured maximum of 600 seconds. The Desktop still clamps the value at ten minutes, so recording is not unbounded.
- Empty or failed transcription is retried exactly once with the same in-memory audio `Blob`.
- The retry helper never writes audio to disk, browser storage, the runtime database, or Git.
- A second failure remains visible as a failure; Hermes never pretends the request was captured.

## Personality policy

`SOUL.md` now asks for warm charisma plus occasional dry Jarvis-style wit or light sarcasm in casual, low-stakes interaction. Guardrails make accuracy and usefulness primary:

- no forced joke in every response;
- no mockery, repeated catchphrases, or theatrical role-play;
- no sarcasm when Syed is frustrated, confused, rushed, or reporting a failure;
- serious literal language for professional output, factual corrections, finance, tax, legal, health, security, and sensitive matters;
- humour follows the answer and never changes evidence, citations, context separation, or action policy.

The obsolete two-sentence spoken-answer rule was removed. Hermes should speak the complete useful final answer, honor explicit requests for brevity/detail, omit hidden reasoning/tool traces, and use at most one truthful short acknowledgement while work is running.

## Verification

- Marked-root safety preflight: pass.
- Native focused tests: 84 passed across five files.
- TypeScript typecheck: pass.
- Production Desktop build and package: pass; no development server used.
- Live configuration: `silence_duration=5.5`, `max_recording_seconds=600`, existing `auto_tts=true` preserved.
- Project and installed `SOUL.md`: identical.
- Hermes Desktop: replaced recoverably and relaunched from `/Applications/Hermes.app`.

## Remaining acceptance

One owner-visible long spoken request with at least one natural two-to-three-second pause should be completed. Hermes should keep listening through the pause and preserve the whole request. This is experiential confirmation, not an unimplemented code path.

## Rollback

The exact prior config, profile, three changed source hooks, and application bundle are preserved outside Git under owner-only:

`~/.hermes/backups/voice-input-personality-20260805T213810Z`

Restore only those named files/bundle after fully quitting Hermes. Do not delete the newer state; preserve it separately if rollback is ever needed.
