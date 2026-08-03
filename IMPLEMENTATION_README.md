# Hermes AI Attention implementation

This repository contains a local-first Python core and a real Hermes project plugin. SQLite/FTS stores derived evidence, tasks, memory proposals, action previews, audits, usage, and incremental checkpoints. A single dated truth is maintained in `implementation/CURRENT_OPERATIONAL_STATE.md`; measured Prompt 4 results are in `implementation/PROMPT_04_ACCEPTANCE_REPORT.md`.

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
HERMES_ACTIONS_KILL_SWITCH=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m hermes_attention.cli health
```

Daily launch:

```bash
./scripts/launch_daily_hermes.sh
```

This prints health, starts the local overlay, and launches Hermes in the trusted project. No dev server, daemon, service, or launch agent is created.

## Boundaries

- The Hermes plugin exposes evidence, task, handoff, screen-request, and exact-preview tools; the restricted Slack executor exists outside the plugin, remains kill-switched, fixed to `#sd-dloa-tyler`, disconnected from a sender, and shadow-only.
- GitHub, Slack, work Google, personal Google, and Zoom have bounded real acceptance. Personal consumer Google uses three project-local GET-only direct-API tools because Google's hosted Workspace MCP Developer Preview rejects consumer accounts; the unsupported personal MCP servers remain disabled. Provider inventory is never treated as acceptance by itself.
- Public web research is read-only and citation-bearing; logged-in browsing, carts, checkout, and payment are unavailable.
- Imported histories and runtime databases remain gitignored.
- ChatGPT official export backfill is live: 47 approved conversations from 1 March 2026 onward are indexed as source evidence with idempotent reruns. Current split-shard exports and explicit context relay are supported; continuous account synchronization is not claimed.
- The root handoff `README.md` is protected; implementation commands live here and in `docs/runbooks/`.
- Historical milestone records may describe earlier states; `implementation/CURRENT_OPERATIONAL_STATE.md` is the dated current authority.
