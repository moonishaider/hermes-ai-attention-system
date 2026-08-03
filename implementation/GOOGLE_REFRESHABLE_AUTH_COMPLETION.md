# Google refreshable authorization completion

Checked: 4 August 2026

## Problem resolved

The original Google Workspace MCP OAuth flow stored six independent access tokens without refresh tokens. Each expired after approximately one hour, producing repeated consent requests.

## Implemented design

- One work-account offline grant and one personal-account offline grant.
- Exactly four scopes per grant: Gmail read-only, Drive read-only, Calendar-list read-only, and Calendar-events read-only.
- `access_type=offline`, explicit consent, state validation, PKCE, exact loopback redirect, normal TLS certificate validation, and exact granted-scope validation.
- Owner-only token storage outside Git, backup before initial replacement, atomic updates, and an account lock around refresh.
- Automatic refresh before the daily launcher health check and on direct API access.
- Optional refresh-token expiry tracking; access and refresh health never expose token values.
- Separate work/personal and Gmail/Drive/Calendar logical tools remain host-locked GET-only. No create, modify, send, upload, delete, or response method exists.

## Provider fallback decision

The Google Workspace MCP Developer Preview accepted separate resource tokens but rejected one combined account grant. Keeping it would require three separate grants per account and preserve unnecessary consent friction. Both accounts therefore use the standard official Gmail, Drive, and Calendar APIs through six bounded project tools. All six preview MCP server records are disabled in the backed-up Hermes configuration.

## Live proof

- Work: refresh token issued; forced refresh passed; Gmail, Drive, and Calendar metadata smokes passed.
- Personal: app moved from Testing to In production; refresh token issued with no lifetime field; forced refresh and all three metadata smokes passed.
- Combined refresh command reports both accounts `ready-refreshable`.
- External-action kill switch remains active and generic Slack sending remains unavailable.
- No token value or private result content was printed, logged, or committed.

## Verification warning

The personal application is In production but unverified. Google therefore displays a warning because the scopes access user data. Formal verification is not required for this private single-user deployment; it would mainly remove the warning and support broader distribution. Google may still revoke refresh tokens after user revocation, credential rotation, account-security events, prolonged non-use, or organization session policy.

Official references checked:

- https://developers.google.com/identity/protocols/oauth2/web-server
- https://developers.google.com/identity/protocols/oauth2/resources/best-practices
- https://support.google.com/cloud/answer/15549945

## Rollback

Code rollback: `bf04f22`. Runtime rollback copies are recorded in `implementation/EXTERNAL_WRITE_LOG.md`. Restore only the exact backed-up token/configuration files and revoke the newer Google grant manually; do not perform broad cleanup.
