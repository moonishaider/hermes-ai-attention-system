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
project-local ignored `backups/` directory, including timestamped
`Jarvis-before-final-voice-ui-*.app` and `Jarvis-before-voice-delivery-*.app`
copies. Keep them project-local and inspect the exact path before any restore.
Restoring means quitting Jarvis, moving the current exact app to a new backup
name, copying one reviewed rollback app to `/Applications/Jarvis.app`, verifying
its deep signature, and reopening it. Never broadly delete or overwrite the
only copy.
