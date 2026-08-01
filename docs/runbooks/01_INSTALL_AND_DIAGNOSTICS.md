# Install and diagnostics runbook

1. Confirm the shell is in the marked repository root with `pwd` and `./scripts/preflight_safety.sh`.
2. Run `./scripts/verify_safety_controls.sh`.
3. Use Python 3.11 or newer. No package installation is required for the core.
4. Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/config_doctor.py`.
5. Run `./scripts/run_tests.sh` and `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/secret_scan.py`.
6. Install official Hermes `v0.19.1` separately following its official instructions; do not copy credentials into this repository.
7. Review `.hermes/plugins/hermes-attention`, then set `HERMES_ENABLE_PROJECT_PLUGINS=true` only in the deliberate Hermes launch environment.
8. Merge `hermes/config.example.yaml` into the existing Hermes configuration; do not overwrite it. Keep computer, browser, terminal, and MCP connectors disabled initially.
9. Compare `hermes/SOUL.md` with any existing Hermes home `SOUL.md`. Copy or merge it manually only after review.
10. Launch Hermes from the marked project root using the normal installed command. This project does not require or permit a local dev server.
11. In Hermes, call only the status tool first. Confirm `external_writes_enabled=false`, expected contexts, disabled connectors, and budget status.

API keys are entered only into the provider’s supported secret store or environment outside Git. Add DeepSeek first for routine/difficult routes, then OpenAI for Luna/Terra. Run one synthetic, low-token direct API smoke test per route and record model ID, date, success, latency, and cost locally. If V4 Pro lacks the required endpoint, keep difficult routing disabled or use its documented chat-completions path; do not silently substitute Sol.
