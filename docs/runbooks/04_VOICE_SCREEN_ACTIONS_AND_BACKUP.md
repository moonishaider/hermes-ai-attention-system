# Voice, screen, actions, and backup runbook

## Voice and visible status

Hermes provides native voice mode. Configure the chosen supported TTS provider outside Git, then start voice with Hermes `/voice`. Keep a text transcript/status surface visible. The optional local overlay can be started only deliberately with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m hermes_attention.cli overlay`; it reads JSON status events from standard input, provides mute/cancel/dismiss controls, and does not capture the screen. Stop it when the session ends.

## Screen viewing

1. Ask the assistant to prepare a screen-view request with an explicit reason and context.
2. Verify its state says `awaiting-explicit-local-capture` and `capture_performed=false`.
3. Syed manually grants the narrow macOS Screen Recording permission to the chosen Hermes application only if desired.
4. Capture only the intended window/region through the reviewed `OneShotScreenCapture` adapter. Its macOS interactive selector is the visible capture indicator, its grant token is consumed before capture, and it writes no image file or automatic retention record.
5. Use GPT-5.6 Luna for the supplied image. Do not enable continuous viewing, broad computer control, or automatic retention.
6. Revoke the macOS permission when no longer needed. The adapter is implemented and tested locally but is not registered as an unrestricted Hermes/computer-use tool.

## Supervised action testing

1. Use a synthetic destination and payload.
2. Generate an A2 proposal. Review context, destination, browser profile, payload, evidence, expiry, idempotency key, and preview hash.
3. Confirm the current policy returns `shadow-only` and `execution_performed=false`.
4. Change one payload field locally and confirm preview-hash validation fails. Test unknown/mixed and A4 rejection locally.
5. The restricted executor exists but is deliberately absent from Hermes tools and remains kill-switched. It accepts only the fixed Inside Success daily-update action, exact workspace/channel, stored approved state, unexpired proposal, matching preview hash, and idempotency policy.
6. Do not clear the kill switch or test through a real Slack sender until Syed selects the fixed destination and explicitly approves the exact synthetic supervised test. Calendar, email, download, browser, payment, deletion, and account/permission hooks remain disabled.

## Backup and restore

1. Stop any process using the local database.
2. Create a non-overwriting backup: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/backup_runtime.py runtime-data/hermes_attention.sqlite3 backups/hermes-attention-YYYYMMDD.sqlite3`.
3. Validate the backup with `sqlite3 BACKUP_PATH 'PRAGMA integrity_check;'` and expect `ok`.
4. To restore, keep the current database as a separate recoverable file, copy the reviewed backup to a new explicit runtime filename, validate it, and point configuration to it. Never overwrite the only copy or use broad deletion.
