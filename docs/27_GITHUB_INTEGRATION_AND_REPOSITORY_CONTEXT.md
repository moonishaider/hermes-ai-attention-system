# GitHub Integration and Repository Context

## Purpose

GitHub is a first-class evidence source for the assistant because much of Syed’s real work occurs in code repositories. It should help Hermes understand active projects, code/documentation, recent commits, pull requests, issues, decisions, blockers, and completed work without mixing company and personal contexts.

## Owners to verify

- `moonishaider`: Syed’s personal GitHub owner/account, containing personal, portfolio, side-project, and potentially client-related repositories.
- `inside-success`: the company owner/account used by Syed’s department and containing company projects.

Codex must verify whether each string is a user or organization and what the authenticated identity can actually read. Never assume private-repository access merely because public repositories are visible.

## Build repository

The Hermes system itself should be documented and versioned in a dedicated **private** repository under `moonishaider`, preferably:

`moonishaider/hermes-ai-attention-system`

If a suitable existing private repository already exists, Codex may use it after documenting why. It must not overwrite an unrelated repository. No implementation code or documentation should be pushed into `inside-success`.

## Hermes runtime connection design

Use the current official GitHub MCP server or another official GitHub-supported interface, connected through Hermes MCP support.

Configure two logical connections:

1. `github_personal_readonly`
2. `github_inside_success_readonly`

They remain part of one visible Hermes assistant and one initial profile; separate connections do not create separate bots or duplicate model costs.

Each connection should use:

- separate credentials or independently scoped authorization;
- read-only server mode;
- the smallest useful toolsets/tools;
- repository-owner allowlists and optional per-repository allowlists;
- runtime tool inventory checks;
- negative tests that attempted writes fail;
- separate audit attribution.

## Initial capabilities

Hermes should be able to:

- list accessible repositories;
- read repository metadata, default branches, READMEs, selected files, and code search results;
- inspect recent commits and Syed’s contribution activity;
- read issues, pull requests, reviews, discussions where available, and status/check information needed for project awareness;
- answer source-backed questions about a project;
- resume a project after inactivity;
- use relevant GitHub activity as evidence for the Inside Success daily activity report;
- identify stale branches, unresolved reviews, failed checks, open blockers, and repeated work as suggestions only.

It should not clone or index every repository continuously. Prefer live MCP/API retrieval plus selective cached summaries. Clone only when a specific coding task requires a working tree.

## Provenance schema

Every GitHub evidence record should retain:

- connection/account identity;
- owner and repository;
- repository visibility;
- object type;
- default/current branch;
- commit SHA or immutable object identifier;
- path and line range when applicable;
- issue/PR/discussion number when applicable;
- author/actor;
- created/updated/retrieved timestamps;
- semantic context labels and confidence;
- sensitivity and permitted-use policy.

Owner/repository metadata is immutable provenance. The AI may add semantic labels such as Inside Success, personal, Mitchell, mixed, or unknown, but must not replace the source identity.

## Context behavior

- Content from `inside-success` defaults to the `inside-success` semantic context unless evidence supports `mixed` or another explicit project tag.
- Content from `moonishaider` is classified by repository metadata/configuration and evidence, not automatically treated as personal.
- A repository can be mapped to multiple contexts.
- Outgoing professional content must not include unrelated personal or client repository information.
- New owners and repositories are configuration entries, not architectural changes.

## Write policy

Hermes GitHub access is read-only in the initial production version.

Possible later approval-gated personal actions may include preparing an issue or draft pull-request description, but they are not part of the initial authority. Company GitHub writes remain disabled unless Syed explicitly authorizes a narrowly scoped workflow in a future policy change.

Codex itself may write only to the dedicated private project repository under `moonishaider` during implementation. This build-time authorization does not grant the finished Hermes assistant GitHub write access.

## Security and validation

- Verify the exact current GitHub MCP read-only behavior rather than trusting the flag name.
- Inspect the exposed tool list and reject any unexpected write/admin/secret-management tools.
- Use fine-grained tokens or OAuth permissions with minimal repository access when available.
- Never grant administration, secrets, deploy-key, organization-management, billing, package deletion, workflow write, or repository deletion permissions.
- Respect company SSO/organization approval requirements.
- Store credentials outside Git and never print them.
- Record connector freshness and authorization failures clearly.
