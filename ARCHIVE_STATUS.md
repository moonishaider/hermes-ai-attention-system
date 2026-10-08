# Personal project preservation — 8 October 2026

This is a personal Jarvis/Hermes research project. It is not a client deliverable or a company-owned project, and does not represent an employer or client.

The default branch contains the latest preserved implementation. Development is paused; this is an archival checkpoint, not a claim that the assistant is ready for daily use. Historical milestones and test reports describe the checks performed at their dates.

Public code and documentation are separated from private runtime material. Real account emails and configured Slack workspace/channel/user and OAuth app/client identifiers have been replaced with examples in the reachable branch history. These examples cannot be used to connect to the original accounts. Historical company/client context names are integration labels, not project ownership or affiliation.

Do not commit credentials, personal source data, runtime databases, diagnostic exports, screenshots, or private handoffs. Original private state and original Git history are preserved separately in an encrypted, private owner-controlled archive; the recovery key is not on GitHub. Do not merge old clones or old history back into this repository.

## Restarting development

- Clone this repository afresh. Both `main` and `feat/personal-assistant` have sanitized history; old commit IDs changed during privacy cleanup.
- Start with `README.md`, `IMPLEMENTATION_README.md`, and `implementation/` for architecture and implementation evidence. Historical safety policies may require a new explicit owner scope before fresh work.
- Reinstall dependencies from the repository lockfiles and documented requirements. Toolchains, node_modules, build output, Python environments and local databases are deliberately absent from public Git.
- Populate local private configuration with accounts you control. Review enabled integrations and all action policies before starting anything; example identifiers are not production configuration.
- If restoring the owner's exact prior state, use the separate private archive's README and recovery key. Restore into a staging directory first; dependency reinstalls and provider reauthorization may be necessary.

## Privacy-check limits

The archive review scanned reachable Git history for credential patterns and compared selected configured credential values without displaying them. No live credential match was identified. Public issues/PRs, releases and Actions artifacts were empty at the audit, and wiki/discussions were disabled. These bounded checks do not prove that no historical or third-party copy exists. Rewriting branch history cannot recall copies already downloaded, and GitHub may retain unreachable objects or cached commit views.
