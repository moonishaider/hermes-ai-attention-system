# Start Hermes

## Open it

Double-click **Launch Hermes.command** in this project folder. A Terminal window is the Hermes chat, and the small Hermes status overlay appears beside it. Wait until the Hermes prompt appears.

## Type or speak

- Type a request at the Hermes prompt and press Return.
- For voice, type `/voice on`, press Return, then use `Control+B` to start and stop recording. Ryan speaks the reply.
- Say `stop` while Ryan is speaking to interrupt him, or type `/voice off` to end voice mode.

## View one screen region

Ask: `Look at one screen region once and explain what you see in personal context.`

Hermes opens Apple's visible region selector. Drag over only the window or region you want to share, then confirm the capture. Press Escape to cancel. It uses GPT-5.6 Luna once, retains no screenshot, does not continuously watch the screen, and cannot click or type for you.

## Controls

- **Cancel** stops the active model response.
- **Mute** or **Unmute** changes spoken output for this launch.
- **Dismiss** hides the small overlay; the Terminal chat remains open.
- Type `/exit` in the Terminal chat to close Hermes normally. Do not use `/exit --delete` unless you intentionally want to delete that session history.

## Healthy startup

Healthy startup ends at the Hermes prompt with the overlay showing **Hermes ready; external actions killed**. The health output should show the approved Flash/Pro/Luna/Terra routes, refreshable Google accounts, `external_actions.enabled: false`, `kill_switch: true`, and no generic Slack sender.

The launcher uses Hermes's pinned Python 3.11 runtime directly, so double-clicking it does not depend on Terminal's PATH or Apple's older system Python.

## Normal limitations

- A simple reply normally starts quickly. Source-backed multi-service work can take roughly one to three minutes; Hermes should show that it is checking sources rather than guessing.
- Very short speech can be misheard by local Whisper. Repeat the phrase or type it when precision matters.
- Zoom may refresh its access token on first use. A refreshable expired access token is not the same as a disconnected account.
- Screen understanding requires a fresh visible selection every time.
- Slack/email sending, calendar changes, logged-in browser control, checkout/payment, continuous ChatGPT sync, and continuous screen viewing remain unavailable.

Useful first requests:

- `Give me a concise Inside Success attention brief with sources and confidence labels. Do not send anything.`
- `Resume the Hermes project from Codex and GitHub evidence and tell me the next open loop.`
- `Find my Mitchell open loops and unanswered questions, keeping Mitchell separate from Inside Success.`
