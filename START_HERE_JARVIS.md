# Start Here — Jarvis

Open **Jarvis** from Applications, Finder, Spotlight, or the Dock. It opens its own protected Hermes backend; no Terminal window is required.

## Everyday use

- Press **Command–Shift–Space** anywhere for Quick Entry, type naturally, and press Return.
- Press **Control–Option–Space** or click the always-visible **Talk** button. Talk cancels any current answer, then changes to **Stop listening** while recording. If capture or delivery fails, Jarvis keeps it only in memory and offers **Retry transcription**, **Edit transcript**, and **Discard**. If its live and final transcripts strongly disagree, Jarvis submits nothing and asks you to review the transcript; a successful Hermes receipt releases the raw audio.
- In the main window, choose the correct context before work: Inside Success, Personal, Mixed, Unknown, or the preserved dormant Mitchell context.
- Use **Attention → Select area** for one explicit screen selection. Only that selection is interpreted; the screenshot is discarded.
- Use **Stop speaking** to silence audio immediately, **Cancel** to stop a running request, and **Quit Jarvis completely** from the menu-bar icon to stop Jarvis and its owned backend.

## What healthy looks like

The lower-left status says **Systems nominal**. Chat acknowledges immediately, shows the selected route and each source/tool as it runs, then shows the final answer plus latency, token count, and estimated cost. The Attention page shows the context’s Work Ledger count and model-budget state.

## Local intelligence

Projects shows living project state. Missions, Radars, and Capability Studio can create bounded local records. Capability Studio only saves a draft and performs a local dry run; it cannot widen tools, OAuth scopes, protected code, or external-action authority.

Settings → **Guided navigation** can preview and open a small reviewed set of pages in the correct existing Chrome profile. It always shows the profile, account, domain, context, and action first. It cannot accept an arbitrary URL, type, submit, download, change settings, or control the computer generally.

## Normal limitations

- Wake phrase is off and not implemented in this Jarvis build; the two global shortcuts are the supported activation paths.
- Personal Calendar creation and Gmail draft creation are implemented behind narrow wrappers but remain disabled because project safety rules prohibit Codex from performing real calendar/email writes.
- Company/client writes, generic Slack sending, payments, checkout, unrestricted browser/computer control, and Gmail sending are unavailable.
- Guided navigation currently opens fixed pages or performs one bounded public search. Automatic page reading, scrolling, and form interaction are not claimed in this release.
- Closing the window keeps Jarvis available in the menu bar. Launch at Login is an explicit, default-off setting.
