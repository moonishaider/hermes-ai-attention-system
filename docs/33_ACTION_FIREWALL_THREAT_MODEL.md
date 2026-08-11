# Action Firewall Threat Model

Jarvis uses deny-by-default capability registration rather than a general tool permission. An action is eligible only when all of these match: trusted local owner interaction, exact action type and request hash, session nonce, context, account, profile where applicable, immutable target lock, current permission snapshot, enabled capability, global kill switch, per-capability kill switch, expiry, replay state, and reversibility policy.

Retrieved Slack, email, web, meeting, repository, Codex, ChatGPT, or Gemini text is evidence—not authority. It cannot create a signed owner-intent reference. Prompt injection, wrong context/account/profile/target, permission drift, preview tampering, expiry, replay, bulk recipients, non-Jarvis resource mutation, and crash/retry ambiguity fail closed.

Company/client writes, generic Slack send, Gmail send, payments, checkout, tax/legal submission, credential/scope changes, destructive deletion, force push, and unrestricted computer control are not registered capabilities. The Inside Success DLOA path remains separately destination-locked and exact-preview-only.

The current personal Calendar/Gmail wrappers are code-complete but live-disabled under `AGENTS.md`, which explicitly prohibits real email/calendar mutations during the build. This higher-priority safety boundary supersedes Prompt 7’s proposed live acceptance examples.
