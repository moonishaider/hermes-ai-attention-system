# First-Use Defect Fixes — 6 August 2026

## Owner reports

Syed found that a natural pause could submit a voice turn before he finished, an Inside Success “yesterday” request used the Pakistan civil date instead of the Miami work date, and a basic absence summary took too long. No Slack message or other external write was requested or performed.

## Diagnosis

- Hermes Desktop used its supported default three-second VAD silence boundary.
- Relative dates were not represented in the context registry, so the model could inherit the machine date.
- Redacted timing metadata showed the absence brief enumerated Slack channels twice, returned a 103,875-character broad search result, performed many channel reads, expanded to about 59k input tokens, and used seven model calls. Provider reads were generally sub-two-second; orchestration and payload growth dominated latency.

## Corrections

- Set supported `voice.silence_duration` to 5.5 seconds while keeping explicit End and Stop controls.
- Added explicit `America/New_York` for Inside Success and `Asia/Karachi` for Personal. Mitchell currently uses Asia/Karachi; Mixed and Unknown deliberately have no single timezone.
- Added `hermes_attention_context_time`, which resolves today/yesterday/tomorrow to exact local, UTC, and Unix bounds. Ambiguous contexts fail closed.
- The tool returns a bounded Slack/Calendar recipe: one initial Slack search, maximum 20 concise results, no surrounding context, no channel enumeration, then selective relevant thread reads.
- Updated SOUL and stable USER guidance so relative dates are resolved before retrieval and mixed-context windows are labeled separately.

## Verification

- The midnight-boundary test proves that at 00:30 in Karachi on 6 August it is still 5 August in Miami, so Inside Success “yesterday” resolves to 4 August while Personal “yesterday” resolves to 5 August.
- 64 project tests pass, including new ambiguous-context fail-closed and plugin-inventory coverage.
- Configuration doctor, secret scan, marked-root preflight, and all safety-control negative tests pass.
- Runtime config reports `silence_duration: 5.5`; the relaunched app loaded one additional deferred project tool, confirming the new tool inventory.
- The changes are configured and loaded. A real voice-pause turn and one bounded Inside Success absence brief remain owner-visible acceptance checks; they are not falsely marked accepted.

## Rollback

Use Git commit `9ecbaec` as the code rollback point. Preserve the current database first, then restore the matching owner-only pre-merge configuration/SOUL/USER backup under `~/.hermes/backups/`. A new non-overwriting project database backup was also created under `backups/` and is ignored by Git.
