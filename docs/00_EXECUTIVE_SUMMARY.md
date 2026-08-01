# Executive Summary

## Product

A single Hermes-based **AI Attention & Intelligence System** for Syed Moonis Haider. It unifies awareness across approved sources, maintains operational memory and tasks, provides persistent on-demand specialists, supports voice and explicit screen context, and introduces external actions through narrow approval-controlled interfaces.

## Architectural verdict

Use Hermes as the runtime shell and integration host, but keep the following as independent, replaceable boundaries:

- context/provenance model;
- specialist registry;
- history bridge;
- evidence index;
- policy engine;
- action executor;
- overlay UI;
- evaluation and cost accounting.

Prefer native Hermes features and official MCP/native integrations. Custom services are a fallback, not the starting assumption.

## One assistant, not many bots

There is one visible assistant and initially one Hermes profile. Specialist capabilities persist as modules with their own scoped memory, tools, templates, and tests. They are invoked on demand. Temporary subagents are used only for isolated reasoning, parallel work, or independent review.

## Initial context model

- `inside-success`
- `mitchell`
- `personal`
- `mixed`
- `unknown`

These are configurable records, not hard-coded application branches. Every source item retains immutable provenance.

## Main value

- prevents forgotten commitments and missed work;
- reduces time spent checking Slack, email, meetings, Codex, and tasks;
- rapidly reconstructs project state;
- gives concise attention and context-switch briefings;
- writes a source-backed daily company activity report;
- finds repeated work worth automating;
- preserves evidence so advice can be verified.

## Safety

External systems begin read-only. The assistant may update its own memory and task state. External writes pass through a separate narrow executor with exact preview and user approval. High-impact actions remain manual.

## Hosting and cost

Start locally on an 8 GB Apple Silicon Mac with API-hosted models and lightweight SQLite-based state. Consider a small CPU VPS only after 24/7 monitoring proves valuable. Target under $50/month; no permanent GPU VPS.

## Approved model baseline

- DeepSeek V4 Flash — default/routine work
- DeepSeek V4 Pro — difficult reasoning
- GPT-5.6 Luna — vision/screens
- GPT-5.6 Terra — rare high-stakes independent review
- direct API billing; do not use the ChatGPT/Codex subscription allowance

## Latest build and GitHub decisions

Codex builds the project with GPT-5.6 Sol/Medium in Full Access without per-command approvals, using the hard safety protocol in Doc 15. GitHub is a first-class source with separate read-only connections for `moonishaider` and `inside-success`; the implementation itself is stored in a dedicated private repository under `moonishaider` and never pushed to company repositories.

