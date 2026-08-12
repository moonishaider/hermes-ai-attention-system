# Jarvis Architecture and Hermes Adapter

**Checked:** 12 August 2026

Jarvis is a Tauri 2 + React/TypeScript desktop shell over the accepted Hermes 0.20.0 intelligence stack. It does not reimplement the agent and does not replace the existing evidence, context, connector, memory, skill, budget, or action-policy layers.

## Trust boundaries

1. The WebView renders local bundled assets only. Its CSP permits no remote scripts or arbitrary network access.
2. Rust owns a random, process-memory-only bearer credential and the exact `hermes gateway run` child it starts.
3. Jarvis asks macOS for one fresh loopback port per launch, then its owned Hermes gateway binds only `127.0.0.1:<private dynamic port>`. Rust calls the authenticated `/health/detailed`, `/v1/runs`, SSE events, and stop endpoints. Neither the port nor bearer credential reaches React, logs, Git, or command output. A full quit closes the gateway; a relaunch cannot inherit the prior aiohttp listener's macOS teardown state.
4. React may call only typed Tauri commands. There is no shell, process, arbitrary URL, arbitrary filesystem, generic HTTP, updater, or browser-control command.
5. Voice, one-shot screen understanding, and local-state operations use three exact Python adapters. Rust validates schemas and sizes before invoking them; the renderer cannot select an executable or path.

## Runtime lifecycle

- The single-instance plugin is registered first. A second launch focuses the existing window.
- Closing a window hides it. The native menu-bar item reopens it.
- Full Quit cancels Jarvis activity and kills only the exact Hermes gateway child owned by Jarvis.
- Launch at Login uses Tauri’s visible macOS autostart integration and is off by default.
- No custom daemon, launch agent, local development server, Docker service, or Postgres service exists.

## Hermes API compatibility

The installed Hermes source is the official 0.20.0 tag (`v2026.8.3`, commit `3c27eb6`) plus the already accepted local voice/MCP/UI patches. The stable authenticated API supports run submission, structured progress, SSE text deltas, cancellation, session state, tools, and runtime-model selection. It does not advertise realtime voice, audio, or memory-write APIs; Jarvis therefore uses narrow local adapters rather than pretending those HTTP features exist.

## State ownership

The project’s existing SQLite database remains the sole attention/intelligence store. Tauri never opens it directly. Python owns schema migrations, evidence, the Work Ledger, projects, missions, radars, capabilities, model decisions, actions, and audit state. Live connector results must enter immutable evidence before becoming durable ledger state.
