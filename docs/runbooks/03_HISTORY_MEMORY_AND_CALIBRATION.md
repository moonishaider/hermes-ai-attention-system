# History, memory, and calibration runbook

## Codex history

1. Preview only: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m hermes_attention.cli codex-history preview`.
2. Confirm the displayed Codex home, file count, and byte count. No file content is printed.
3. Ingest a bounded first batch: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m hermes_attention.cli codex-history ingest --maximum-records 100`.
4. Inspect local search/context results. Incremental checkpoints prevent rescanning completed lines.

## ChatGPT historical backfill

1. In ChatGPT, use the official Settings data-export workflow. Download the export manually.
2. Place the ZIP temporarily under the gitignored `imports/` directory.
3. Preview, choosing an explicit start date: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m hermes_attention.cli chatgpt-export preview imports/EXPORT.zip --start-date YYYY-MM-DD`.
4. Review selected conversation count. Import only after that review by repeating with action `import` and `--confirmed`.
5. Remove the downloaded export manually when no longer needed using a recoverable method; do not commit it.

There is no supported continuous ChatGPT personal-history API in this design. For ongoing context, create a small JSON relay matching `tests/fixtures/synthetic/context-relay.json`, save it under gitignored `context-inbox/private/`, and run `context-relay PATH`. The relay must name its source reference and context labels.

## Calibration

1. Add only synthetic or user-approved representative samples.
2. Review classifications for personal, Inside Success, Mitchell, mixed, and unknown.
3. Correct rules in `config/contexts.json`; never hide mixed evidence by choosing a winner automatically.
4. Review extracted commitments as `triage`; promote them manually only after checking evidence.
5. Review proposed memory and contradictions. Confirm, reject, or supersede; do not silently overwrite.
6. Compare attention ranking with actual urgency and adjust deterministic priority/due-date policy through a reviewed change.
