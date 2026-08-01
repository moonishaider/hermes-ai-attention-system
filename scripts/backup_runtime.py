#!/usr/bin/env python3
"""Create a consistent SQLite backup at one explicit project-local destination."""

import argparse
from pathlib import Path
import sqlite3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve()
    if not source.is_file():
        parser.error("source database does not exist")
    if destination.exists():
        parser.error("destination already exists; backups never overwrite")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as original, sqlite3.connect(destination) as backup:
        original.backup(backup)
    print(f"Backup created: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
