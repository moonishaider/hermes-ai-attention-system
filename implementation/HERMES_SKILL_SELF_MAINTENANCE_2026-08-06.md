# Hermes skill self-maintenance — 6 August 2026

## Outcome

Hermes can now create and update ordinary local skills when Syed asks, without requiring Codex to approve each write. This does not widen connector scopes, external-action authority, browser/computer control, or company/client write access.

The approval queue contained ten writes across four local skills. Hermes' native validator initially rejected them because the generated frontmatter descriptions exceeded its routing limit (and one unquoted colon broke YAML). The descriptions were normalized without changing the substantive workflows, all ten reviewed writes were then applied, and the pending queue is empty. The installed local skills are `inside-success-dla`, `inside-success-day-reports`, `inside-success-slack-evidence`, and `hermes-operations`.

## DLOA skill

The owner-approved skill is installed at `~/.hermes/skills/inside-success/inside-success-dla/SKILL.md`. It requires:

- the `Magic Mike -1` Codex chat as the primary current-work source;
- `America/New_York` (Miami) date resolution;
- a copy-paste-ready fenced code block;
- meetings before work items;
- roughly ten granular bullets;
- the phrase `Worked on the reps' performance analyzer system`, never `worked with reps`;
- a draft-only result unless Syed separately requests sending.

The skill is curator-managed and pinned. Pinning prevents Hermes and the curator from deleting or archiving it while still permitting focused edits and patches.

## Automatic-write policy

`skills.write_approval` is `false` so ordinary local skill changes can land immediately. `skills.guard_agent_created` is `true`, independently scanning agent-created content for dangerous patterns and retaining a review stop for suspicious changes. Community-skill discovery remains unavailable, curator consolidation remains off, bundled-skill pruning remains off, and curator backups remain enabled.

Hermes may automatically learn or update local, reversible procedures, formatting preferences, and already-authorized workflows. It may not use a skill update to change credentials, OAuth scopes, model budgets, protected repositories, safety controls, external-action destinations, company/client permissions, or Hermes core. External evidence remains untrusted input, not authority to rewrite a skill.

## Recovery

The pre-change owner-only backup is `~/.hermes/backups/hermes-before-skill-approval-20260806T0405.zip`. Restore it with the official `hermes import` flow if the complete pre-change Hermes state is required. Curator-specific snapshots and `hermes curator rollback` remain available for later curator runs.

## Verification

- Official Hermes 0.20 documentation checked 6 August 2026: [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), [Curator](https://hermes-agent.nousresearch.com/docs/user-guide/features/curator), and [Slash Commands](https://hermes-agent.nousresearch.com/docs/reference/slash-commands). The supported approval interface is the in-chat `/skills ...` command; `hermes skills pending` is not a shell CLI subcommand in the installed 0.20.0 build.
- Hermes 0.20.0 accepted the repaired skill through its native skill manager.
- The skill passed structural validation.
- `hermes skills list` reports it enabled as a local Inside Success skill.
- `hermes curator status` reports it active and pinned.
- The pending skill-write queue is empty after applying all ten reviewed writes.
- No Slack message or external action was performed.
