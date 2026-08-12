# Jarvis Rollback and Uninstall

## Roll back project source

Prompt 7 began at commit `af4b330`, tagged `prompt7-pre-jarvis-20260812`. Inspect before changing anything. Use ordinary non-destructive Git operations; do not reset, clean, rewrite history, or force push.

## Restore data/config safely

- Hermes/config/state backup: `~/.hermes/backups/prompt7-pre-jarvis-20260811T195914Z`
- Database backup: `backups/hermes-attention-before-prompt7-20260811T195914Z.sqlite3`

Restore a backup to a new path first and verify hashes/integrity before any switch. Never overwrite the only current or backup copy.

## Stop or remove Jarvis

Choose **Quit Jarvis completely** from its menu-bar item. Confirm the Jarvis process and its owned loopback gateway are gone. Removing `/Applications/Jarvis.app` is optional and must be an explicit, exact-target user decision; it does not delete Hermes configuration or the project database. The stock Hermes Desktop remains independent.

## Installed-app rollback copies

The immediately preceding signed application packages are preserved under the
project-local ignored `backups/` directory. The exact app immediately before
the final cosmetic simplification is
`backups/Jarvis-pre-ui-simplification-20260812T171700Z.app`; the installed final
Auto Explicit Request binary has SHA-256
`b8449a4ef1b4e7d9759c369483cb6030079662d12fdbe23c90f7197bd48c0a10`.
The immediately preceding installed package is preserved as
`backups/Jarvis-pre-final-audited-20260812T174840Z.app`.
The online database backup immediately before Auto Explicit acceptance is
`backups/prompt7-pre-auto-explicit-20260812T170515Z.sqlite3` and passed
`PRAGMA quick_check=ok`.
The final accepted database backup and restore drill are
`backups/prompt7-complete-20260812T173008Z.sqlite3` and
`backups/prompt7-complete-20260812T173008Z-restore-check.sqlite3`; both passed
SQLite `quick_check=ok` and share SHA-256
`25baa42b880ca721aa401ee92ed0f678823e05ca5c083fb642b4b2c208c11d1c`.
Keep them project-local and inspect the exact path before any restore.
Restoring means quitting Jarvis, moving the current exact app to a new backup
name, copying one reviewed rollback app to `/Applications/Jarvis.app`, verifying
its deep signature, and reopening it. Never broadly delete or overwrite the
only copy.

## Personal-action rollback

In Jarvis → Actions, select **Turn personal actions off** first. This leaves any
existing personal event or draft unchanged while disabling both registered
execution capabilities. The separate owner-only token is
`~/.hermes/mcp-tokens/google_personal_actions.json`; do not remove it through an
automated cleanup. If revocation is desired, revoke the exact Jarvis personal
Google grant from the Google Account UI, then preserve the local record in a
new dated owner-only backup before any manual retirement. A Jarvis-created
calendar event should be reversed only through its exact **Undo this event**
control; Jarvis has no Gmail-send or draft-delete operation.
