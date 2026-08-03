# Milestone 04: Destination-Locked DLOA Preview

**Date:** 4 August 2026

**Pre-change rollback:** `09717a6`

**External Slack writes:** none

Syed confirmed `#sd-dloa-tyler` as the department DLOA channel and confirmed that `#sd-eat-that-frog-tyler` is not the destination. The read-only Slack connection resolved the approved destination to workspace `T01K1TNLXLK`, channel `C0B0RT26KCZ`, and Syed user `U0AUU3UBBEW`.

Six of Syed's previous posts were inspected read-only to determine formatting. The persistent configuration records only the resulting convention: a dated `DLOA` heading, primary bullets, and nested bullets for substantial technical work. Private message content was not copied into Git.

The fixed action configuration now requires:

- action `publish_inside_success_daily_update`;
- context `inside-success`;
- the exact workspace and channel above;
- Syed as the approval identity;
- a 15-minute exact-preview lifetime;
- no generic Slack-send exposure;
- no broad Slack mentions;
- at most 8,000 characters;
- supervised-preview mode.

`scripts/build_daily_report_draft.py` converts a previously accepted, write-disabled real-data result into an owner-only, Git-ignored draft and evidence-hash manifest. It rejects failed acceptance, leakage, uncertain claims, cross-context claims, missing provenance, overwrites, and paths outside the private acceptance directory. `scripts/prepare_daily_report_preview.py` creates the exact proposal and private preview while forcing external writes off and the kill switch on. It contains no sender.

A real-data preview for 3 August was produced privately from the accepted same-day attribution result. Strict provenance matching retained one fully resolved confirmed claim; unresolved or uncertain claims were omitted rather than guessed. The preview was not sent. This is a safe acceptance artifact, not yet a sufficiently complete daily report.

The test suite now has 49 passing tests. New negative coverage confirms wrong-channel rejection, mass-mention rejection, expiry rejection, replay rejection, and the exact production lock. The existing tests continue to prove that the Hermes plugin exposes no executor and that the default kill switch blocks writes while permitting reads.

The remaining human gate is review and explicit approval of one exact, unexpired payload. A real Slack sender must not be connected or invoked before that gate.
