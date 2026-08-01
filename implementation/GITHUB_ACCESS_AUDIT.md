# GitHub Access Audit

**Checked:** 2026-08-01
**Authenticated identity:** `moonishaider`

## Read visibility

- `moonishaider` is a user owner. The authenticated listing returned 21 public and zero private personal repositories.
- `Inside-Success` is an organization. The authenticated listing returned 38 repositories, including 27 private repositories.
- Organization membership is active. Private visibility proves access is not public-only, but does not prove visibility of every organization repository.

## Credential posture

The build-time GitHub CLI credential currently exposes `repo`, `read:org`, `workflow`, and `gist` scopes. It is sufficient for the guarded private project repository, but is intentionally broader than the finished Hermes runtime connections should receive. It must not be reused as a Hermes runtime credential.

## Destination decision

- Authorized build destination: private `moonishaider/hermes-ai-attention-system*` only.
- Preferred repository `moonishaider/hermes-ai-attention-system` did not exist or was not visible during Prompt 1.
- `inside-success` is read-only and never a build destination.
- Repository creation and pushes must use `scripts/safe_create_private_repo.sh` and `scripts/safe_git_push.sh`.
