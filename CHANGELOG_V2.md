# v2 Change Log

This revision preserves all original architecture and product requirements while applying Syed’s latest decisions:

- Codex builder changed to GPT-5.6 Sol at Medium reasoning.
- Codex changed to Full Access with no approval prompts.
- Added a strict two-prompt flow: acknowledgement first, implementation second.
- Added project-local PreToolUse/SubagentStart hooks, forbidden command rules, project/symlink preflight, guarded GitHub creation/push scripts, bypass tests, and package validation.
- Added GitHub as a first-class Hermes evidence source for `moonishaider` and `inside-success`, initially read-only.
- Added a dedicated private implementation repository under `moonishaider`; no build or runtime writes to `inside-success`.
- Kept the Hermes runtime model router unchanged: DeepSeek V4 Flash, DeepSeek V4 Pro, GPT-5.6 Luna, and rare GPT-5.6 Terra review.
- Preserved all previous requirements for contexts, persistent specialists, history, memory/tasks, voice/overlay, screen/browser controls, daily reporting, extensibility, cost, safety, and future staged actions.

Full Access still carries residual risk that project rules cannot eliminate. The package therefore requires a dedicated project directory, a current backup, Git checkpoints, no secret-bearing tracked files, and strict external destinations.
