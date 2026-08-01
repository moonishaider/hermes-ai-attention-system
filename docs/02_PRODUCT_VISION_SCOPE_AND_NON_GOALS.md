# Product Vision, Scope, and Non-Goals

## Vision

Create a personal operating layer that helps Syed understand what deserves attention, remember what matters, and safely move work forward across company, client, and personal contexts.

The assistant should answer:

- What changed?
- What do I need to act on?
- What did I promise?
- What is blocked?
- What decisions conflict?
- What was I doing before I switched context?
- What can be ignored?
- What repeated work should become an automation?
- What evidence supports this answer?

## Product principles

1. **Evidence before confidence.**
2. **One visible assistant; modular intelligence behind it.**
3. **Immutable provenance; flexible interpretation.**
4. **Capabilities are removed or constrained technically, not only by prompts.**
5. **Fast acknowledgement; accuracy-first final answers.**
6. **Build useful workflows before decorative personality.**
7. **Extensibility without multi-agent theatre.**
8. **Direct API cost control and measurable ROI.**
9. **Local-first state where practical; no heavy local inference.**
10. **Actions are staged and reversible wherever possible.**

## In scope

- Hermes runtime/desktop setup and configuration.
- Context and provenance routing.
- Persistent specialist registry.
- Memory, evidence, task, commitment, and decision systems.
- Codex history ingestion.
- ChatGPT historical import and ongoing context relay.
- Slack, Gmail, Calendar, Zoom, selected files, web, and screen sources.
- Voice input/output and a live overlay.
- Attention queue, context handoffs, meeting intelligence, project resumption.
- Shopping/product research.
- Daily Inside Success activity report.
- Controlled browser/computer actions and action approvals.
- Audit, tests, evaluations, backups, cost limits, optional later VPS.

## Non-goals for the first production release

- A fully autonomous company run by dozens of agents.
- Continuous screen or microphone uploading.
- Unrestricted computer control.
- Autonomous payments, purchases, tax filing, legal filing, credential changes, or destructive deletion.
- Storing every raw message as trusted memory.
- Running frontier-size local models on the 8 GB Mac.
- A permanent GPU VPS.
- AIOS or another agent kernel merely to appear advanced.
- A custom FastAPI/n8n integration layer when Hermes or an official MCP already solves the need securely.
- Perfect unsupported real-time sync of a personal ChatGPT account.

## Added scope: GitHub awareness

GitHub project awareness is in scope: separate read-only access to `moonishaider` and `inside-success`, project/code/documentation retrieval, commit/PR/issue context, and contribution evidence. Generic or autonomous GitHub writes are not in scope for Hermes version one.

