# Voice, screen, actions, and backup runbook

## Voice and visible status

Hermes native voice is configured for local faster-whisper STT and Edge TTS. Start daily use with `./scripts/launch_daily_hermes.sh`, then use Hermes `/voice on`; Ctrl+B is push-to-talk and spoken stop phrases/keyboard interruption remain the native cancellation path. The bundled free openWakeWord `Hey Hermes` detector remains off until the real microphone acceptance succeeds, then `/wake on` may enable it deliberately. The overlay displays heard text, current status, streamed reply, context/source, and mute/cancel/dismiss controls; it never captures the screen. The launcher stops it when Hermes exits.

Grant Microphone permission only to the exact process macOS presents for this guarded launch. Test a short non-sensitive phrase, transcription, Flash reply, Edge playback, mute/interruption, and warm/cold latency. If local faster-whisper is not conversationally usable, benchmark one supported low-cost cloud STT before changing the default; keep local as fallback.

## Screen viewing

1. Ask the assistant to prepare a screen-view request with an explicit reason and context.
2. Verify its state says `awaiting-explicit-local-capture` and `capture_performed=false`.
3. Syed manually grants narrow macOS Screen Recording permission only when the one-shot test is ready.
4. Capture only the intended window/region through the reviewed `OneShotScreenCapture` adapter. Its macOS interactive selector is the visible capture indicator, its grant token is consumed before capture, and it writes no image file or automatic retention record.
5. The prepared acceptance command is `PYTHONPATH=src python3 scripts/run_screen_acceptance.py --reason "Prompt 4 one-time reviewed window" --context personal --confirmed-one-shot`. It opens the system interactive selector, sends only the in-memory PNG to GPT-5.6 Luna, and retains no pixels.
6. Do not enable continuous viewing, broad computer control, Accessibility permission, or automatic screenshot retention.
7. Revoke the macOS permission when no longer needed. The adapter is not registered as an unrestricted Hermes/computer-use tool.

## Supervised action testing

1. Use a synthetic destination and payload.
2. Generate an A2 proposal. Review context, destination, browser profile, payload, evidence, expiry, idempotency key, and preview hash.
3. Confirm the current policy returns `shadow-only` and `execution_performed=false`.
4. Change one payload field locally and confirm preview-hash validation fails. Test unknown/mixed and A4 rejection locally.
5. The restricted executor exists but is deliberately absent from Hermes tools and remains kill-switched. It accepts only the fixed Inside Success daily-update action, exact workspace/channel, stored approved state, unexpired proposal, matching preview hash, and idempotency policy.
6. The selected Slack destination is workspace `T01K1TNLXLK`, channel `#sd-dloa-tyler` (`C0B0RT26KCZ`). Build private previews with `scripts/build_daily_report_draft.py` and `scripts/prepare_daily_report_preview.py`. Do not clear the kill switch or connect a real sender until Syed reviews and explicitly approves the exact unexpired payload/hash. Calendar, email, download, browser, payment, deletion, and account/permission hooks remain disabled.

## Backup and restore

1. Stop any process using the local database.
2. Create a non-overwriting backup: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/backup_runtime.py runtime-data/hermes_attention.sqlite3 backups/hermes-attention-YYYYMMDD.sqlite3`.
3. Validate the backup with `sqlite3 BACKUP_PATH 'PRAGMA integrity_check;'` and expect `ok`.
4. To restore, keep the current database as a separate recoverable file, copy the reviewed backup to a new explicit runtime filename, validate it, and point configuration to it. Never overwrite the only copy or use broad deletion.
