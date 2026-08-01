# Connector activation records

These templates describe the exact logical connections that onboarding will activate one at a time. They contain no credentials or OAuth tokens. Runtime connection state remains under `~/.hermes`, outside Git.

Every connection starts disabled and read-only. After OAuth, onboarding must inspect the actual `tools/list` result, reject write/admin tools, apply the include list in `config/integrations.json`, run one metadata-only read smoke, and record only non-sensitive provenance/status evidence in `runtime-data/`.

Current official remote routes checked 1 August 2026:

- GitHub remote MCP at the provider-enforced `/readonly` route with separate fine-grained personal/company tokens and repository-owner boundaries. Hermes cannot dynamically register a GitHub OAuth client, so its safe 404 OAuth attempt was replaced by GitHub's documented PAT fallback; the broad build credential is never reused.
- Slack MCP at `https://mcp.slack.com/mcp`; a registered internal/directory app and workspace approval are required, and the server exposes writes unless the client inventory is filtered.
- Google Workspace MCP is Developer Preview and uses separate Gmail, Drive, and Calendar endpoints. The exact read-only OAuth scopes and write-tool exclusions are in the registry.
- Zoom MCP requires a Zoom Marketplace integration point, OAuth scopes, product licensing, and a server URL selected for the relevant Zoom product. Activation remains blocked until those are known.

No broad build-time GitHub credential may be reused at runtime. Company Chrome is reserved for Inside Success. Profile 1 is used for personal and Mitchell/client authorization.

The two Slack manifests are intentionally separate and contain only read/search/history user scopes. They contain no `chat:write`, conversation creation, reaction write, canvas write, bot, command, webhook, or admin scope. Fixed loopback callback ports let Hermes use Slack's confidential OAuth flow without a local development server; the callback listener exists only during the interactive consent transaction.
