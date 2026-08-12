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
project-local ignored `backups/` directory. The exact app before the final
default-off personal-action build is
`backups/Jarvis-pre-default-off-personal-actions-20260812T154336Z.app`;
the installed final-candidate binary has SHA-256
`be2a11627fb6659a9aa36f7afa944152f903d56dbba2d3e8f95a885b147b9f4b`.
The final database backup and restore drill is preserved under
`backups/prompt7-final-20260812T211500Z`; both copies passed SQLite
`quick_check=ok`. Keep them project-local and inspect the exact path before any restore.
Restoring means quitting Jarvis, moving the current exact app to a new backup
name, copying one reviewed rollback app to `/Applications/Jarvis.app`, verifying
its deep signature, and reopening it. Never broadly delete or overwrite the
only copy.

## Personal-action rollback

In Jarvis → Actions, select **Disable personal actions** first. This leaves any
existing personal event or draft unchanged while disabling both registered
execution capabilities. The separate owner-only token is
`~/.hermes/mcp-tokens/google_personal_actions.json`; do not remove it through an
automated cleanup. If revocation is desired, revoke the exact Jarvis personal
Google grant from the Google Account UI, then preserve the local record in a
new dated owner-only backup before any manual retirement. A Jarvis-created
calendar event should be reversed only through its exact **Undo this event**
control; Jarvis has no Gmail-send or draft-delete operation.
