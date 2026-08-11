# Prompt 7 Compatibility Record — 12 August 2026

- Hermes official stable remains 0.20.0 / release `v2026.8.3` from 3 August 2026. The installed checkout is exact tagged commit `3c27eb6` plus 15 previously accepted local voice/MCP/UI changes; those changes were preserved.
- Jarvis uses Hermes’s authenticated loopback `/v1/runs`, SSE events, stop, health, and runtime-selection contract. Hermes advertises no audio, realtime-voice, or memory-write API, so narrow local adapters are used.
- Tauri packages are exact and locked: Tauri 2.11.5, CLI 2.11.4, API 2.11.1, build 2.6.3, single-instance 2.4.3, global-shortcut 2.3.2, autostart 2.5.1, notification 2.3.3.
- Build toolchains are project-local and ignored: Node 24.18.1 LTS and Rust stable 1.97.1. No shell profile or global runtime was changed.
- The package is ad-hoc signed for this local Mac. No Apple Developer identity exists, so external distribution/notarization is not available. That does not block local use.
- Vite is used only for a static production build. No Vite/Tauri development server was run.
- Provider model IDs and prices were rechecked in the project configuration. Luna is $0.20/$1.20 and Terra $2/$12 per million input/output tokens; Flash and Pro retain the verified DeepSeek values.
