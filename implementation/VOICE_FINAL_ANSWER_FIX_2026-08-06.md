# Voice Final-Answer Fix

**Date:** 6 August 2026

**Scope:** Hermes Desktop voice narration only

**External actions:** none

## Reported problem

The previous response projection made spoken answers artificially short. It instructed the model to provide at most 45 spoken words, placed the remaining useful material after `Details for screen:`, and stopped TTS at that marker. Separately, tool-calling turns could expose interim narration to TTS. In real use, Hermes could spend time reading working commentary and then speak only the first two lines of the answer.

## Corrected behavior

- During a slow tool-backed turn, Hermes speaks one immediate neutral acknowledgement: “I'm checking that now.”
- Detailed interim narration, tool chatter, and reasoning bubbles remain unspoken.
- When the final answer arrives, Hermes speaks the complete final answer shown in chat.
- The same interim filter applies when the visible automatic-read-aloud toggle is enabled.
- The model is no longer forced into a 45-word response or a screen-only details section.
- If Syed explicitly asks for a brief summary, the model should answer briefly in the normal way; otherwise speech follows the complete final response.
- Existing Stop speaking, barge-in, mute, wake phrase, 5.5-second end-of-speech window, routing, connectors, and safety controls are unchanged.

## Implementation and evidence

The project-owned Hermes 0.20.0 compatibility patch now changes only final-answer selection and bounded acknowledgement behavior. The installed source was backed up before modification, rebuilt with Node 24, packaged without a development server, and installed over only `/Applications/Hermes.app`. The prior app remains recoverable outside Git.

Validation completed:

- native `chat-messages` and speech sanitizer tests: 69/69 passed;
- native Desktop TypeScript typecheck: passed;
- native production build and unpacked macOS package: passed;
- packaged application contains the acknowledgement and contains neither the old voice contract nor the `Details for screen:` speech boundary;
- project Prompt 6 Desktop contract tests: passed;
- no model route, connector, credential, external-action, or filesystem authority changed.

One real tool-backed spoken turn is still required to confirm the human experience. Automated checks cannot establish whether the timing and phrasing feel right to Syed.

## Rollback

Quit Hermes and restore the exact previous app from `~/.hermes/backups/voice-final-answer-fix-20260806T204629Z/Hermes-before-fix.app`. The same owner-only backup contains the pre-change source files and their hashes. Do not publish that backup.
