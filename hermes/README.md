# Hermes runtime adapter

The project plugin under `.hermes/plugins/hermes-attention` exposes local status, retrieval, attention, handoff, task, screen-request, and preview-only action tools. It exposes no action executor and no connector write tool.

Project plugins are disabled by Hermes unless `HERMES_ENABLE_PROJECT_PLUGINS=true`. Review this repository first, set that variable only for the marked project, and launch Hermes from the project root. Copy `hermes/SOUL.md` into the configured Hermes home only after comparing it with any existing personality file. Merge `hermes/config.example.yaml` rather than overwriting an existing Hermes configuration.

External MCP connections remain absent from the example until the account-specific read-only authorization runbooks are completed. Use per-server `tools.include` controls and provider read-only mode; never rely only on prompt instructions to block writes.
