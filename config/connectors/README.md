# Connector activation records

These templates describe the exact logical connections that onboarding will activate one at a time. They contain no credentials or OAuth tokens. Runtime connection state remains under `~/.hermes`, outside Git.

Every connection starts disabled and read-only. After OAuth, onboarding must inspect the actual `tools/list` result, reject write/admin tools, apply the include list in `config/integrations.json`, run one metadata-only read smoke, and record only non-sensitive provenance/status evidence in `runtime-data/`.

Current official remote routes checked 2 August 2026:

- GitHub remote MCP at the provider-enforced `/readonly` route with separate fine-grained personal/company tokens and repository-owner boundaries. Hermes cannot dynamically register a GitHub OAuth client, so its safe 404 OAuth attempt was replaced by GitHub's documented PAT fallback; the broad build credential is never reused.
- Slack MCP at `https://mcp.slack.com/mcp`; a registered internal/directory app and workspace approval are required, and the server exposes writes unless the client inventory is filtered.
- Google Workspace MCP is Developer Preview and uses separate Gmail, Drive, and Calendar endpoints. The exact read-only OAuth scopes and write-tool exclusions are in the registry.
- Zoom uses the official unified endpoint at `https://mcp.zoom.us/mcp/zoom/streamable` for the four reviewed read tools. The work account and product prerequisites are verified. Activation remains disabled until Zoom Marketplace recovers from its observed Cloudflare 526 error and the private user-managed General App can be created with exactly the four scopes in `config/integrations.json`.

No broad build-time GitHub credential may be reused at runtime. Company Chrome Profile 2 is reserved for Inside Success, including Zoom. Profile 1 is used for personal and Mitchell/client authorization.

The two Slack manifests are intentionally separate and contain only read/search/history user scopes. They contain no `chat:write`, conversation creation, reaction write, canvas write, bot, command, webhook, or admin scope. Fixed loopback callback ports let Hermes use Slack's confidential OAuth flow without a local development server; the callback listener exists only during the interactive consent transaction.

The pinned MCP SDK follows the MCP scope-selection strategy by replacing an explicitly configured scope with every scope in Slack's protected-resource metadata, including writes. The project-owned `slack-oauth` command therefore makes the reviewed allowlist authoritative, validates the callback state and PKCE exchange, rejects every extra granted scope, and atomically creates Hermes-compatible mode-600 token state. This is the required route for Slack; do not use generic `hermes mcp login` for these connections.

Both Slack connections are live and isolated. Inside Success uses company Chrome, app `A0BMF36RS9X`, callback port 8765, and `slack_inside_success_readonly`; Mitchell uses Profile 1, app `A0BN85H7Y80`, callback port 8766, and `slack_mitchell_readonly`. Each exposes only the same seven search/read tools and explicitly excludes messaging and other writes.
