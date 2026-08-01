# Compatibility Report

**Checked:** 2026-08-01
**Status:** Complete for implementation baseline

This report records implementation-time verification against current official primary sources. Exact versions, capability decisions, and fallback boundaries will be completed before the Milestone 0 gate.

| Area | Current finding | Implementation consequence |
|---|---|---|
| Codex | Project hooks, rules, `gpt-5.6-sol`, Medium effort, Never approval, and Full Access configuration are recognized by the installed Codex CLI. | Retain the protected project safety layer and guarded GitHub scripts. |
| Hermes | Tag `v2026.7.30` resolves to package/runtime `v0.19.1`, commit `cc4cab2f592e60a197e796506de9168f74baf3ea`. Project plugins require `HERMES_ENABLE_PROJECT_PLUGINS=1` and the current named-schema registration API. | Installed the exact tag/commit and corrected the plugin contract. The guarded launcher scopes plugin trust to this project; broad tools and prepared MCPs remain disabled. |
| DeepSeek | V4 Flash and V4 Pro are current direct-API models. V4 Pro currently lacks DeepSeek Responses API support while chat/tool-calling is documented. | Use provider/model names as configurable routing policy; use chat-completions adapter for Pro and run a credentialed smoke test before enablement. |
| OpenAI | GPT-5.6 Sol, Luna, and Terra official model pages are current. | Keep Luna vision and rare Terra review configurable through direct API; Sol remains Codex builder-only and is not a Hermes runtime dependency. |
| GitHub | Authenticated read access covers personal public repositories and authorized private Inside Success repositories. | Runtime uses two logical read-only connections; build writes only through guarded scripts. |
| GitHub MCP | Official remote MCP supports provider-level `/readonly`, tool selection, host-managed OAuth, and PAT fallback. Hermes's dynamic OAuth registration received a safe 404 because GitHub requires a host-specific registered app. | Use separate fine-grained tokens through GitHub's documented fallback, `/mcp/readonly`, and Hermes allowlists. Never reuse the broad build credential. Live tool discovery remains required. |
| Google Workspace MCP | Official Gmail, Drive, and Calendar MCPs are Developer Preview and expose read and write tools. A Google Cloud project/client is required. | Six account/product entries are prepared disabled with minimum read scopes in the registry and write exclusions. Activation waits for client/account consent. |
| Slack MCP | Official hosted MCP is GA at `https://mcp.slack.com/mcp`; it requires an internal/directory app, confidential OAuth, workspace approval, and explicit MCP enablement. Its resource metadata advertises both reads and writes, and the pinned MCP SDK replaces configured scopes with that entire advertised set. | Use the project strict-scope OAuth adapter, which requests exactly the reviewed scopes and rejects extras. Inside Success is live with 14 read scopes and seven discovered read/search tools; agent-app experience remains off. Mitchell remains separate and disabled. |
| Zoom MCP | Hosted MCP requires a Marketplace integration point, product-specific URL/scopes, permissions, and licensing. | Registry remains disabled; do not invent a universal tool surface. Use the official API/export fallback if required meeting/recording/transcript tools are unavailable. |
| ChatGPT history | Official supported historical path is user data export. No supported continuous personal-history API was identified. | Implement previewed official export backfill plus explicit structured context relay. Do not scrape the account or imply continuous sync. |

## Primary sources checked

- Hermes: [releases](https://github.com/NousResearch/hermes-agent/releases), [providers](https://hermes-agent.nousresearch.com/docs/integrations/providers), [MCP](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/), [plugins](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin/), [memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory), [voice](https://hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode), [computer use](https://hermes-agent.nousresearch.com/docs/user-guide/features/computer-use).
- Providers: [DeepSeek pricing/models](https://api-docs.deepseek.com/quick_start/pricing/), [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra).
- Connectors: [GitHub MCP configuration](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md), [Google Workspace MCP](https://developers.google.com/workspace/guides/configure-mcp-servers), [Google MCP security](https://developers.google.com/workspace/guides/configure-mcp-security), [Slack MCP](https://docs.slack.dev/ai/slack-mcp-server/), [Zoom MCP skill](https://github.com/zoom/skills/blob/main/skills/zoom-mcp/SKILL.md).
- History: [ChatGPT data export](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data).

Versions and hosted-tool inventories can drift. `scripts/config_doctor.py` validates local shape, but a credentialed read-only smoke test remains mandatory after each connector is authorized.
