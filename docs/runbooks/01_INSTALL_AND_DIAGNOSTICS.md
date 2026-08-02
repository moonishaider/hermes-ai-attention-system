# Install and diagnostics runbook

1. Confirm the shell is in the marked repository root with `pwd` and `./scripts/preflight_safety.sh`.
2. Run `./scripts/verify_safety_controls.sh`.
3. Use Python 3.11 or newer. The core is stdlib-only; public search uses the reviewed optional `ddgs==9.14.4` pin in the Hermes virtual environment.
4. Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/config_doctor.py`.
5. Run `./scripts/run_tests.sh` and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/secret_scan.py`.
6. Official Hermes `v0.19.1` is installed outside the repository; do not copy credentials into Git.
7. The reviewed `.hermes/plugins/hermes-attention` plugin is enabled only by the guarded launch scripts.
8. Project Hermes configuration and SOUL are merged into the existing Hermes home with timestamped backups. Never overwrite the only copy.
9. Use `./scripts/launch_daily_hermes.sh` for the health view, overlay, and interactive Hermes session, or `./scripts/launch_hermes.sh` for Hermes without the overlay. Neither starts a dev server or persistent service.
10. The daily launcher prints health first. Confirm `external_writes_enabled=false`, `kill_switch=true`, expected routes, token warnings, Codex checkpoint, and connector state.

API keys remain outside Git in owner-readable Hermes secret storage. DeepSeek Flash/Pro and OpenAI Luna/Terra passed representative bounded tests; Flash remains the routine default and Sol remains builder-only.
