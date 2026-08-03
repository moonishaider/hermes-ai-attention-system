#!/usr/bin/env python3
"""Refresh both account-scoped Google read-only grants without printing secrets."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.google_offline_oauth import GOOGLE_ACCOUNTS, GoogleOfflineOAuthError, GoogleOfflineTokenManager  # noqa: E402


def main() -> int:
    manager = GoogleOfflineTokenManager()
    results = []
    failed = False
    for account in GOOGLE_ACCOUNTS:
        try:
            results.append(manager.refresh_account(account))
        except GoogleOfflineOAuthError as exc:
            results.append({"account": account, "state": "authorization-required", "reason": str(exc)})
            failed = True
    print(json.dumps({"accounts": results, "secrets_printed": False}, sort_keys=True))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
