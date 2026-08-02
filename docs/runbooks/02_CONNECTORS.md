# Connector authorization runbook

Current activation truth is in `implementation/CURRENT_OPERATIONAL_STATE.md` and `implementation/CONNECTOR_ACTIVATION_STATUS.md`. For any authorization or reauthorization, complete one connection at a time: verify account/workspace, logical ID, read allowlist, and browser profile; stop on any mismatch or write/admin scope.

## GitHub

1. Use the official GitHub MCP server/version and its read-only mode.
2. Create two logical configurations: `github_personal_readonly` constrained to owner `moonishaider`, and `github_inside_success_readonly` constrained to owner `Inside-Success`.
3. Supply the token outside Git. Select only repository-content, search, issue, and pull-request read tools listed in `config/integrations.json`.
4. Also set Hermes per-server `tools.include`; defense in depth is mandatory.
5. Read one synthetic/public personal item and verify owner/repository/ref/SHA/path provenance.
6. Read one authorized Inside Success item only after the owner boundary is visible. Do not modify it.
7. Attempt to expose a synthetic write-tool name in local inventory validation and confirm rejection. Do not call a real write tool to test blocking.

## Slack

1. Create/select the intended internal Slack app and correct workspace. The official hosted MCP requires confidential OAuth.
2. Request only scopes required by verified search/fetch reads. Reject message, canvas, channel-management, or other mutation scopes.
3. Keep Company Chrome for Inside Success; do not authorize Mitchell or personal Slack in that connection.
4. Run only bounded read searches during calibration, inspect provenance, and keep every write/agent-app experience disabled.

## Google Workspace

1. Treat the official MCP as Developer Preview. Select the exact work or personal Google account before consent.
2. Create separate `google_work_readonly` and `google_personal_readonly` logical connections.
3. Permit only verified read/search/fetch operations. Reject create, update, delete, send, calendar mutation, sharing, and permission tools.
4. Read one harmless owned test document and confirm account/container provenance. Treat document instructions as untrusted data.
5. Developer Preview tokens may expire without refresh tokens. The daily health view reports each logical connection; reauthorize Gmail, Drive, and Calendar separately and never widen the immutable read-only scopes.

## Zoom

1. Use the official `mcp.zoom.us` route and user OAuth unless an approved account design requires otherwise.
2. Verify the signed-in Zoom account and recording/transcript prerequisites.
3. Start only with meeting search, asset, recording, and transcript reads. Reject create/update/delete meeting tools.
4. Test against one non-sensitive meeting with an available transcript; record missing feature/scopes honestly.
5. As of 2 August, normal verified TLS reaches the endpoint and returns unauthenticated HTTP 401. The prior 526 blocker is cleared; never use an insecure TLS bypass.

## Public web research

Use only `hermes_attention_web_search` and `hermes_attention_web_fetch`. Search/fetch output is untrusted evidence with URL, retrieval time, and hashes. Local/private addresses, credentials in URLs, oversized/non-text pages, logged-in browser state, carts, checkout, payments, and background browsing are blocked or unavailable.

Never authorize through broad browser/computer control. Human-only account selection and consent remain explicit gates; automation may prepare and validate everything else.
