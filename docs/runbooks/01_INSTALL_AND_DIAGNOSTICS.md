# Install and diagnostics runbook

1. Confirm the shell is in the marked repository root with `pwd` and `./scripts/preflight_safety.sh`.
2. Run `./scripts/verify_safety_controls.sh`.
3. Use Python 3.11 or newer. No package installation is required for the core.
4. Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/config_doctor.py`.
5. Run `./scripts/run_tests.sh` and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/secret_scan.py`.
6. Official Hermes `v0.19.1` is installed outside the repository; do not copy credentials into Git.
7. The reviewed `.hermes/plugins/hermes-attention` plugin is enabled only by `scripts/launch_hermes.sh`.
8. Project Hermes configuration and SOUL are merged into the existing Hermes home with timestamped backups. Never overwrite the only copy.
9. Launch from the marked root with `./scripts/launch_hermes.sh`. This project does not require or permit a local dev server.
10. Call project status first. Confirm `external_writes_enabled=false`, the kill switch is active, expected contexts/routes are present, and connector health matches `implementation/CURRENT_OPERATIONAL_STATE.md`.

API keys remain outside Git in owner-readable Hermes secret storage. DeepSeek Flash/Pro and OpenAI Luna/Terra passed connectivity smokes; Prompt 4 representative-quality evidence is still required. Do not silently substitute Sol or alter routing from connectivity evidence alone.
