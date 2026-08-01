# Milestone 02 — Operational onboarding foundation

Checked: 1 August 2026

## Completed

- Installed official Hermes Agent `v0.19.1 (2026.7.30)` from tag `v2026.7.30`, commit `cc4cab2f592e60a197e796506de9168f74baf3ea` under `~/.hermes`.
- Preserved pre-project and pre-tightening copies of Hermes configuration under Git-ignored `backups/`. Project SOUL and configuration were merged without replacing unrelated defaults.
- Added `scripts/launch_hermes.sh`. It runs preflight, enables the reviewed project plugin only for this launch, and keeps the external-action kill switch on by default. It never enables YOLO/computer use and does not start a development server.
- Set native routine chat to direct DeepSeek `deepseek-v4-flash`; added audited direct routes for `deepseek-v4-pro`, `gpt-5.6-luna`, and `gpt-5.6-terra`. `gpt-5.6-sol` remains builder-only.
- Added resumable onboarding, hidden-input provider-secret setup, bounded Codex ingestion from 1 March 2026, one-shot screen capture, a fixed-destination supervised executor, and disabled future action hooks.
- Installed pinned Hermes voice, Edge TTS, and wake extras plus PortAudio. A synthetic Edge TTS to local faster-whisper transcription passed without microphone access.
- Prepared ten disabled remote MCP entries for two GitHub identities, two Slack workspaces, and work/personal Gmail, Drive, and Calendar. They have explicit allowlists; no OAuth was initiated and no runtime credential exists.
- Created and pushed the private repository through guarded scripts: `https://github.com/moonishaider/hermes-ai-attention-system`.

## Safety outcome

Hermes status was called before any conversational launch. The gateway is stopped, scheduled jobs are zero, provider keys are absent, external writes are disabled, and messaging platforms are unconfigured. The supported inventory shows only the project toolset, memory, session search, todo, STT, and TTS enabled. Terminal, file, web, browser, image/video generation, BFL, delegation, computer use, cron, and home automation are disabled.

The supervised executor is not registered as a Hermes tool. It requires the kill switch to be deliberately cleared, live policy enablement, exact stored approved state/hash, an unexpired proposal, and one fixed Inside Success workspace/channel. Its tests use a synthetic sender; no real Slack message was sent.

During PortAudio installation, Homebrew automatically removed its pre-existing ripgrep formula during cleanup. Codex's bundled ripgrep remained present. The Homebrew formula was immediately restored with auto-update and cleanup disabled. No other cleanup was requested or performed.

## Remaining human-only gates

Provider credentials are next. Connector OAuth then proceeds one connection at a time. Microphone and Screen Recording permissions remain unrequested. No ChatGPT export is selected. Real calibration and the first destination-locked Slack publish remain semantic/external-action approvals.

