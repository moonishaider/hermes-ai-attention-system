#!/usr/bin/env python3
"""Plan or apply exact, reversible quarantine of reproducible Jarvis artifacts.

This tool deliberately has no deletion mode. Project safety policy requires
project-local quarantine and a committed plan instead of automated deletion.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any, Iterator


MARKER = ".hermes-ai-attention-project"
MANIFEST_VERSION = 1
ALLOWLIST = {
    "rust-target": ("jarvis/src-tauri/target", "reproducible-rust-build"),
    "frontend-dist": ("jarvis/dist", "reproducible-frontend-build"),
    "node-modules": ("jarvis/node_modules", "lockfile-reproducible-dependencies"),
    "npm-cache": (".tooling/npm-cache", "reproducible-package-cache"),
}
PROTECTED_PREFIXES = (
    ".codex", ".git", ".hermes", "backups", "config", "docs", "implementation",
    "runtime-data", "scripts", "src", "tests", "PROMPT_08_JARVIS_PRODUCT_HARDENING_GOAL.md",
)


def project_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    if not (root / MARKER).is_file():
        raise RuntimeError("marked Jarvis project root not found")
    return root


def _relative(root: Path, path: Path) -> str:
    root_real = root.resolve(strict=True)
    path_real = path.resolve(strict=True)
    try:
        value = path_real.relative_to(root_real).as_posix()
    except ValueError as error:
        raise PermissionError("candidate escapes the marked project root") from error
    if value in PROTECTED_PREFIXES or any(value.startswith(f"{item}/") for item in PROTECTED_PREFIXES):
        raise PermissionError(f"protected path cannot be quarantined: {value}")
    return value


def _tree_entries(path: Path) -> Iterator[Path]:
    if not path.is_dir():
        yield path
        return
    for current, directories, files in os.walk(path, topdown=True, followlinks=False):
        directories.sort()
        files.sort()
        current_path = Path(current)
        yield current_path
        for name in directories:
            candidate = current_path / name
            if candidate.is_symlink():
                yield candidate
        for name in files:
            yield current_path / name


def _tree_fingerprint(root: Path, path: Path) -> tuple[int, int, str]:
    """Return byte count, object count, and a metadata-only tree hash."""
    if path.is_symlink():
        raise PermissionError(f"symlink candidate is forbidden: {path.name}")
    candidate_root = path.resolve(strict=True)
    total = 0
    objects = 0
    digest = sha256()
    for item in _tree_entries(path):
        if item.is_symlink():
            link_target = os.readlink(item)
            try:
                resolved_target = item.resolve(strict=True)
            except OSError as error:
                raise PermissionError(
                    f"broken symlink within candidate is forbidden: {item.relative_to(root)}"
                ) from error
            if resolved_target != candidate_root and candidate_root not in resolved_target.parents:
                raise PermissionError(
                    f"symlink escapes candidate tree: {item.relative_to(root)}"
                )
            relative = item.relative_to(path.parent).as_posix()
            objects += 1
            digest.update(f"{relative}\0symlink\0{link_target}\n".encode())
            continue
        relative = item.relative_to(path.parent).as_posix()
        stat = item.stat(follow_symlinks=False)
        kind = "directory" if item.is_dir() else "file"
        size = stat.st_size if item.is_file() else 0
        total += size
        objects += 1
        digest.update(f"{relative}\0{kind}\0{size}\0{stat.st_mtime_ns}\n".encode())
    return total, objects, digest.hexdigest()


def build_manifest(root: Path, candidate_keys: list[str], created_at: str | None = None) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not (root / MARKER).is_file():
        raise RuntimeError("manifest root is not a marked Jarvis project")
    if not candidate_keys or len(candidate_keys) != len(set(candidate_keys)):
        raise ValueError("candidate list must be non-empty and unique")
    records = []
    for key in sorted(candidate_keys):
        if key not in ALLOWLIST:
            raise PermissionError(f"candidate is not allowlisted: {key}")
        relative, category = ALLOWLIST[key]
        path = root / relative
        if not path.exists():
            raise FileNotFoundError(f"candidate does not exist: {relative}")
        if _relative(root, path) != relative:
            raise PermissionError(f"candidate real path differs from allowlist: {relative}")
        size, objects, fingerprint = _tree_fingerprint(root, path)
        records.append({
            "key": key,
            "path": relative,
            "category": category,
            "size_bytes": size,
            "object_count": objects,
            "metadata_sha256": fingerprint,
        })
    timestamp = created_at or datetime.now(UTC).isoformat()
    identity = sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
    return {
        "version": MANIFEST_VERSION,
        "manifest_id": identity,
        "created_at": timestamp,
        "project_root": str(root),
        "operation": "project-local-quarantine-only",
        "deletion_supported": False,
        "entries": records,
        "total_size_bytes": sum(item["size_bytes"] for item in records),
    }


def _validate_manifest(root: Path, manifest: dict[str, Any]) -> list[tuple[Path, Path, dict[str, Any]]]:
    root = root.resolve(strict=True)
    if manifest.get("version") != MANIFEST_VERSION or manifest.get("operation") != "project-local-quarantine-only":
        raise ValueError("unsupported quarantine manifest")
    if manifest.get("deletion_supported") is not False or Path(str(manifest.get("project_root"))).resolve() != root:
        raise PermissionError("manifest root or policy does not match this project")
    manifest_id = str(manifest.get("manifest_id") or "")
    if not re.fullmatch(r"[0-9a-f]{16}", manifest_id):
        raise ValueError("invalid manifest identity")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest has no entries")
    quarantine = (root / ".workspace-quarantine" / f"prompt8-storage-{manifest_id}").resolve()
    if quarantine.exists() or root not in quarantine.parents:
        raise FileExistsError("exact quarantine destination already exists or escapes the project")
    validated = []
    seen: set[str] = set()
    for record in entries:
        if not isinstance(record, dict):
            raise ValueError("invalid manifest entry")
        key = str(record.get("key") or "")
        if key not in ALLOWLIST or key in seen:
            raise PermissionError("manifest contains a duplicate or non-allowlisted candidate")
        seen.add(key)
        expected_path, expected_category = ALLOWLIST[key]
        if record.get("path") != expected_path or record.get("category") != expected_category:
            raise PermissionError("manifest path or category differs from the allowlist")
        source = root / expected_path
        if not source.exists() or _relative(root, source) != expected_path:
            raise PermissionError("manifest source is absent or its real path changed")
        size, objects, fingerprint = _tree_fingerprint(root, source)
        if (size, objects, fingerprint) != (
            record.get("size_bytes"), record.get("object_count"), record.get("metadata_sha256")
        ):
            raise RuntimeError(f"candidate changed after manifest generation: {expected_path}")
        destination = quarantine / expected_path
        if destination.exists():
            raise FileExistsError(f"quarantine destination exists: {expected_path}")
        validated.append((source, destination, record))
    return validated


def quarantine_manifest(root: Path, manifest: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    validated = _validate_manifest(root, manifest)
    if dry_run:
        return {
            "ok": True,
            "mode": "dry-run",
            "manifest_id": manifest["manifest_id"],
            "entries": len(validated),
            "total_size_bytes": manifest["total_size_bytes"],
            "freed_bytes": 0,
        }
    moved: list[tuple[Path, Path]] = []
    try:
        for source, destination, _record in validated:
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            moved.append((source, destination))
    except Exception:
        for source, destination in reversed(moved):
            source.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(source)
        raise
    return {
        "ok": True,
        "mode": "quarantined",
        "manifest_id": manifest["manifest_id"],
        "entries": len(moved),
        "total_size_bytes": manifest["total_size_bytes"],
        "freed_bytes": 0,
        "recoverable": True,
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path = path.resolve()
    root = project_root()
    allowed_parent = (root / "runtime-data" / "storage-manifests").resolve()
    if path.parent != allowed_parent or path.suffix != ".json":
        raise PermissionError("manifest destination must be runtime-data/storage-manifests/*.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "dry-run", "quarantine"))
    parser.add_argument("--candidate", action="append", choices=sorted(ALLOWLIST))
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = project_root()
        if args.mode == "plan":
            manifest = build_manifest(root, args.candidate or [])
            write_manifest(args.manifest, manifest)
            result = {"ok": True, "mode": "plan", "manifest": str(args.manifest.resolve()),
                      "manifest_id": manifest["manifest_id"], "entries": len(manifest["entries"]),
                      "total_size_bytes": manifest["total_size_bytes"], "freed_bytes": 0}
        else:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            result = quarantine_manifest(root, manifest, dry_run=args.mode == "dry-run")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError, PermissionError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
