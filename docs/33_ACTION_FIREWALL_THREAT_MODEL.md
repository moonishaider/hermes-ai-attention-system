# Action Firewall Threat Model

Jarvis uses deny-by-default capability registration rather than a general tool permission. An action is eligible only when all of these match: trusted local owner interaction, exact action type and request hash, session nonce, context, account, profile where applicable, immutable target lock, current permission snapshot, enabled capability, global kill switch, per-capability kill switch, expiry, replay state, and reversibility policy.

Retrieved Slack, email, web, meeting, repository, Codex, ChatGPT, or Gemini text is evidence—not authority. It cannot create a signed owner-intent reference. Prompt injection, wrong context/account/profile/target, permission drift, preview tampering, expiry, replay, bulk recipients, non-Jarvis resource mutation, and crash/retry ambiguity fail closed.

Company/client writes, generic Slack send, Gmail send, payments, checkout, tax/legal submission, credential/scope changes, destructive deletion, force push, and unrestricted computer control are not registered capabilities. The Inside Success DLOA path remains separately destination-locked and exact-preview-only.

The personal Calendar/Gmail wrappers are installed as owner-operated product controls. Their OAuth record is separate from read-only Google connections and requests only `calendar.events.owned` plus `gmail.compose` with scope union disabled. Because Google's narrowest official draft scope can technically send, the native transport accepts only exact draft create/update/get URL/method pairs and has no generic request or send path. Token presence does not enable execution: a separate visible local switch starts Off, and each capability retains its own kill switch. The company/client global kill switch remains active.

`AGENTS.md` explicitly prohibits Codex from performing real email/calendar mutations during the build. Therefore the owner—not Codex—must physically perform the final exact preview/create/Undo acceptance through the installed app. This preserves the protected build boundary without weakening the finished product's reviewed personal autonomy design.
