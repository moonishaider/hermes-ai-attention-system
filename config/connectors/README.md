# Connector activation records

These templates describe the exact logical connections that onboarding will activate one at a time. They contain no credentials or OAuth tokens. Runtime connection state remains under `~/.hermes`, outside Git.

Every connection starts disabled and read-only. After OAuth, onboarding must inspect the actual `tools/list` result, reject write/admin tools, apply the include list in `config/integrations.json`, run one metadata-only read smoke, and record only non-sensitive provenance/status evidence in `runtime-data/`.

Current official remote routes checked 1 August 2026:

- GitHub remote MCP with separate personal/company logical authorization and repository-owner boundaries.
- Slack MCP at `https://mcp.slack.com/mcp`; a registered internal/directory app and workspace approval are required, and the server exposes writes unless the client inventory is filtered.
- Google Workspace MCP is Developer Preview and uses separate Gmail, Drive, and Calendar endpoints. The exact read-only OAuth scopes and write-tool exclusions are in the registry.
- Zoom MCP requires a Zoom Marketplace integration point, OAuth scopes, product licensing, and a server URL selected for the relevant Zoom product. Activation remains blocked until those are known.

No broad build-time GitHub credential may be reused at runtime. Company Chrome is reserved for Inside Success. Profile 1 is used for personal and Mitchell/client authorization.
