# Compatibility Report

**Checked:** 2026-08-11
**Status:** Updated through Gemini Takeout acceptance

## Codex current-conversation synchronization (checked 6 August 2026)

The current official Codex App Server documentation exposes local JSONL-RPC
over stdio, `thread/list`, non-mutating `thread/read`, and experimental
paginated `thread/turns/list`. Live testing against installed `codex-cli
0.147.0-alpha.1.2` confirmed initialization, updated-thread listing, and
summary-view turn pagination. Full `thread/read` responses for recent long
chats measured roughly 46–86 MiB because they include tool/reasoning payloads;
the bounded summary turn view measured about 1–4 KiB for ordinary recent turns
and retained the user/assistant fields Hermes needs.

Implementation consequence: current synchronization uses stdio only,
`thread/list` plus summary-view `thread/turns/list`, a 14-day/50-thread/2,000
conversation-item default bound, and a hard method allowlist. Reasoning, tool
calls/results, commands, and images are excluded. The App Server exits after
each sync. `thread/read` is explicitly excluded because the measured full
responses are unnecessary for current-work synchronization. The accepted checkpointed JSONL importer remains
the fallback if the experimental pagination contract changes.

Official source: https://developers.openai.com/codex/app-server

## Gemini Apps export (checked 11 August 2026)

Google's official Gemini Apps Help documents the Takeout route. The delivered archive confirmed that conversational activity is represented by `Takeout/My Activity/Gemini Apps/My Activity.html`, while Gemini-native Gems and scheduled-action metadata use separate HTML pages. Generated media and uploads appear as separate binary files. The importer therefore validates the complete ZIP but reads only those three known HTML members, never extracts or executes archive content, ignores binary attachments and other Google products, requires preview plus explicit confirmation, redacts credential-shaped values, flags prompt injection, groups activities by immutable Gemini chat identifiers, and preserves archive/member/date provenance. The accepted 1 November 2025 backfill inserted 178 duplicate-safe evidence records. Hermes still has no supported continuous personal Gemini-history synchronization route.

Official source: https://support.google.com/gemini/answer/16920332?hl=en

This report records implementation-time verification against current official primary sources. Exact versions, capability decisions, and fallback boundaries will be completed before the Milestone 0 gate.

| Area | Current finding | Implementation consequence |
|---|---|---|
| Codex | Project hooks, rules, `gpt-5.6-sol`, Medium effort, Never approval, and Full Access configuration are recognized by the installed Codex CLI. | Retain the protected project safety layer and guarded GitHub scripts. |
| Hermes | Tag `v2026.7.30` resolves to package/runtime `v0.19.1`, commit `cc4cab2f592e60a197e796506de9168f74baf3ea`. Project plugins require `HERMES_ENABLE_PROJECT_PLUGINS=1` and the current named-schema registration API. | Installed the exact tag/commit and corrected the plugin contract. The guarded launcher scopes plugin trust to this project; broad tools and prepared MCPs remain disabled. |
| DeepSeek | V4 Flash and V4 Pro are current direct-API models. V4 Pro currently lacks DeepSeek Responses API support while chat/tool-calling is documented. | Use provider/model names as configurable routing policy; use chat-completions adapter for Pro and run a credentialed smoke test before enablement. |
| OpenAI | GPT-5.6 Sol, Luna, and Terra official model pages are current. | Keep Luna vision and rare Terra review configurable through direct API; Sol remains Codex builder-only and is not a Hermes runtime dependency. |
| GitHub | Authenticated read access covers personal public repositories and authorized private Inside Success repositories. | Runtime uses two logical read-only connections; build writes only through guarded scripts. |
| GitHub MCP | Official remote MCP supports provider-level `/readonly`, tool selection, host-managed OAuth, and PAT fallback. Hermes's dynamic OAuth registration received a safe 404 because GitHub requires a host-specific registered app. | Use separate fine-grained tokens through GitHub's documented fallback, `/mcp/readonly`, and Hermes allowlists. Never reuse the broad build credential. Live tool discovery remains required. |
| Google OAuth and Workspace MCP | Official guidance requires `access_type=offline` for unattended refresh. Testing-audience authorizations expire after seven days; In production removes that testing limit, while an unverified private app may still show a warning and user cap. Workspace MCP preview endpoints require separate resource-bound tokens and rejected one combined grant; standard Gmail/Drive/Calendar APIs accepted it. | Use one exact four-scope offline grant per account, store it owner-only outside Git, refresh automatically under a lock, monitor optional refresh-token lifetime, and expose six separate host-locked GET-only tools. Disable all six preview MCP endpoints. Formal personal-app verification is deferred for single-user use. |
| Slack MCP | Official hosted MCP is GA at `https://mcp.slack.com/mcp`; it requires an internal/directory app, confidential OAuth, workspace approval, and explicit MCP enablement. Its resource metadata advertises both reads and writes, and the pinned MCP SDK replaces configured scopes with that entire advertised set. | Use the project strict-scope OAuth adapter, which requests exactly the reviewed scopes and rejects extras. Inside Success and Mitchell are live as separate apps/connections, each with 14 read scopes and seven discovered read/search tools; both agent-app experiences remain off. |
| Zoom MCP | On 4 August the official endpoint authorized successfully through a Zoom public client with PKCE. Live discovery returned 12 provider tools rather than the earlier documented nine; the four intended meeting/recording reads are present, as are two provider writes. | Keep the exact four-tool Hermes include list authoritative. OAuth, refreshable token storage, discovery, metadata smoke, and a bounded recent-meeting usefulness case pass. No TLS bypass or provider write tool is exposed. |
| Public web | Hermes bundles DDGS as a supported no-key search backend. The reviewed current PyPI version is `ddgs==9.14.4`. | The project exposes only guarded public search/fetch tools with citations, SSRF/credential/size controls, redaction, and injection flags. Hermes browser remains disabled. |
| ChatGPT history | Official supported historical path is user data export. The 2 August export used five contiguous `conversations-NNN.json` shards rather than one `conversations.json`. No supported continuous personal-history API was identified. | Support the legacy single file and bounded contiguous official shards, require preview plus exact confirmation, preserve evidence provenance, and keep explicit structured context relay. Do not scrape the account or imply continuous sync. |

## Primary sources checked

- Hermes: [releases](https://github.com/NousResearch/hermes-agent/releases), [providers](https://hermes-agent.nousresearch.com/docs/integrations/providers), [MCP](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/), [plugins](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin/), [memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory), [voice](https://hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode), [computer use](https://hermes-agent.nousresearch.com/docs/user-guide/features/computer-use).
- Providers: [DeepSeek pricing/models](https://api-docs.deepseek.com/quick_start/pricing/), [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra).
- Connectors: [GitHub MCP configuration](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md), [Google OAuth offline access](https://developers.google.com/identity/protocols/oauth2/web-server), [Google OAuth audience status](https://support.google.com/cloud/answer/15549945), [Google Workspace MCP](https://developers.google.com/workspace/guides/configure-mcp-servers), [Google MCP security](https://developers.google.com/workspace/guides/configure-mcp-security), [Slack MCP](https://docs.slack.dev/ai/slack-mcp-server/), [Zoom MCP skill](https://github.com/zoom/skills/blob/main/skills/zoom-mcp/SKILL.md).
- History: [ChatGPT data export](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data).

Versions and hosted-tool inventories can drift. `scripts/config_doctor.py` validates local shape, but a credentialed read-only smoke test remains mandatory after each connector is authorized.

Google's earlier Developer Preview flow produced only one-hour access tokens. The replacement direct OAuth flow requested offline access and returned refresh tokens for both accounts. Immediate forced refresh passed. Google may still revoke refresh tokens, so startup health reports access and optional refresh-token expiry without printing token values.
