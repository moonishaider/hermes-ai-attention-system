# Hermes AI Attention implementation

This repository contains a stdlib-only Python core and a real Hermes project plugin. It is intentionally local-first: SQLite/FTS stores derived evidence, tasks, memory proposals, action previews, audits, usage, and incremental checkpoints. Six of seven remote logical connector groups are now enabled read-only; their exact evidence level and remaining acceptance gates are authoritative in `implementation/CURRENT_OPERATIONAL_STATE.md`.

## Safe local checks

From the marked project root:

```bash
./scripts/preflight_safety.sh
./scripts/verify_safety_controls.sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/config_doctor.py
./scripts/run_tests.sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/secret_scan.py
```

Inspect status without a server:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m hermes_attention.cli status
```

No dev server is part of this implementation or runbook. The optional voice/status overlay is a local Tk process and must only be launched deliberately after the overlay runbook is reviewed.

## Boundaries

- The Hermes plugin exposes evidence, task, handoff, screen-request, and exact-preview tools; the restricted Slack executor exists outside the plugin, remains kill-switched, destination-unconfigured, and shadow-only.
- Runtime GitHub, Slack, and Google read-only connections are live. Zoom remains disabled and externally blocked. Provider inventory is never treated as acceptance evidence by itself.
- Imported histories and runtime databases remain gitignored.
- ChatGPT supports official export backfill and explicit context relay, not continuous account synchronization.
- The root handoff `README.md` is protected; implementation commands live here and in `docs/runbooks/`.
- Historical milestone records may describe earlier states; `implementation/CURRENT_OPERATIONAL_STATE.md` is the dated current authority.
