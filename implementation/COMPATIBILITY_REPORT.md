# Compatibility Report

**Checked:** 2026-08-01
**Status:** Complete for implementation baseline

This report records implementation-time verification against current official primary sources. Exact versions, capability decisions, and fallback boundaries will be completed before the Milestone 0 gate.

| Area | Current finding | Implementation consequence |
|---|---|---|
| Codex | Project hooks, rules, `gpt-5.6-sol`, Medium effort, Never approval, and Full Access configuration are recognized by the installed Codex CLI. | Retain the protected project safety layer and guarded GitHub scripts. |
| Hermes | Stable `v0.19.1` was published 2026-07-30. Project plugins use `.hermes/plugins/<name>/plugin.yaml` and `__init__.py`; project plugins require `HERMES_ENABLE_PROJECT_PLUGINS=true`. MCP has per-server include/exclude controls. Native voice supports streaming TTS. | Target `v0.19.1`; ship a real project plugin, a merge-only config example, project context, and a SOUL template. Do not silently enable project plugins, computer use, or external MCP. |
| DeepSeek | V4 Flash and V4 Pro are current direct-API models. V4 Pro currently lacks DeepSeek Responses API support while chat/tool-calling is documented. | Use provider/model names as configurable routing policy; use chat-completions adapter for Pro and run a credentialed smoke test before enablement. |
| OpenAI | GPT-5.6 Sol, Luna, and Terra official model pages are current. | Keep Luna vision and rare Terra review configurable through direct API; Sol remains Codex builder-only and is not a Hermes runtime dependency. |
| GitHub | Authenticated read access covers personal public repositories and authorized private Inside Success repositories. | Runtime uses two logical read-only connections; build writes only through guarded scripts. |
| GitHub MCP | Official server supports `--read-only` and toolset selection. | Require both provider read-only mode and Hermes `tools.include`; preserve owner/repository/ref/SHA/path/issue/PR metadata; expose no runtime write/admin tools. |
| Google Workspace MCP | Official service is Developer Preview and contains both read and write tools; Google explicitly documents prompt-injection risk. | Keep disabled pending account selection; whitelist only verified read/search/fetch tools and treat returned text as untrusted evidence. |
| Slack MCP | Official hosted MCP uses streamable HTTP and confidential OAuth. Its tool surface contains both read and write operations and is limited to internal/Marketplace app distribution. | Keep disabled until the correct workspace/app is selected; permit only search/fetch-style reads and independently exclude sends/creates/updates. |
| Zoom MCP | Official hosted MCP is `mcp.zoom.us`; user OAuth is recommended. Current unified tools cover meeting search/assets/recordings with account and recording prerequisites. | Keep disabled until user OAuth and scopes are reviewed; start with meeting search/transcript/recording reads only. |
| ChatGPT history | Official supported historical path is user data export. No supported continuous personal-history API was identified. | Implement previewed official export backfill plus explicit structured context relay. Do not scrape the account or imply continuous sync. |

## Primary sources checked

- Hermes: [releases](https://github.com/NousResearch/hermes-agent/releases), [providers](https://hermes-agent.nousresearch.com/docs/integrations/providers), [MCP](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/), [plugins](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin/), [memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory), [voice](https://hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode), [computer use](https://hermes-agent.nousresearch.com/docs/user-guide/features/computer-use).
- Providers: [DeepSeek pricing/models](https://api-docs.deepseek.com/quick_start/pricing/), [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra).
- Connectors: [GitHub MCP configuration](https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md), [Google Workspace MCP](https://developers.google.com/workspace/guides/configure-mcp-servers), [Google MCP security](https://developers.google.com/workspace/guides/configure-mcp-security), [Slack MCP](https://docs.slack.dev/ai/slack-mcp-server/), [Zoom MCP skill](https://github.com/zoom/skills/blob/main/skills/zoom-mcp/SKILL.md).
- History: [ChatGPT data export](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data).

Versions and hosted-tool inventories can drift. `scripts/config_doctor.py` validates local shape, but a credentialed read-only smoke test remains mandatory after each connector is authorized.
