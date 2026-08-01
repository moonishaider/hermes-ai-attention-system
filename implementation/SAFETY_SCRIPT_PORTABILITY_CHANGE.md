# Guarded repository script portability change

**Authorized:** Prompt 3, 2026-08-01

## Before

`scripts/safe_create_private_repo.sh` used Bash 4 lowercase expansion for the authenticated login and owner. macOS `/bin/bash` 3.2 stopped at `${LOGIN,,}` before any GitHub operation.

## After

The two values are normalized with POSIX `tr '[:upper:]' '[:lower:]'` and compared exactly. Repository namespace, authenticated identity, existing-origin, existing-repository, private-visibility, and no-push controls are unchanged.

- Prior checksum: `cd3984d491353e5080e858d7c304284067af246d2f066c9d56628bf2c06aff39` (`1797` bytes)
- New checksum: `f126ed947740ecd3db3dcc1c1da09b7b0afb5d895224508d6c7f2e8be0e03b61` (`1955` bytes)

Regression tests execute the real guarded script with a fake `gh` binary under `/bin/bash`. A mixed-case expected identity proceeds to the existing-origin or existing-repository guard according to current publication state, while a wrong identity still stops with exit code 3. No repository creation is performed by these tests.
