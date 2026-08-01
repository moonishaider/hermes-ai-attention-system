"""Configuration loading and boundary validation without third-party dependencies."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import Any


class ConfigurationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"{path} must contain a JSON object")
    return value


def load_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"cannot load {path}: {exc}") from exc


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    root: Path
    runtime_dir: Path
    database: Path
    config_dir: Path
    specialist_dir: Path

    @classmethod
    def discover(cls, start: Path | None = None) -> "ProjectPaths":
        current = (start or Path.cwd()).resolve()
        candidates = (current, *current.parents)
        root = next((p for p in candidates if (p / ".hermes-ai-attention-project").is_file()), None)
        if root is None:
            raise ConfigurationError("marked Hermes project root not found")
        runtime_dir = root / "runtime-data"
        return cls(
            root=root,
            runtime_dir=runtime_dir,
            database=runtime_dir / "hermes_attention.sqlite3",
            config_dir=root / "config",
            specialist_dir=root / "specialists",
        )


def validate_project_configuration(paths: ProjectPaths) -> list[str]:
    errors: list[str] = []
    required = [
        paths.root / ".hermes-ai-attention-project",
        paths.config_dir / "attention.toml",
        paths.config_dir / "contexts.json",
        paths.config_dir / "models.json",
        paths.config_dir / "integrations.json",
        paths.specialist_dir / "registry.json",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing: {path.relative_to(paths.root)}")
    if errors:
        return errors

    try:
        attention = load_toml(paths.config_dir / "attention.toml")
        contexts = load_json(paths.config_dir / "contexts.json")
        models = load_json(paths.config_dir / "models.json")
        integrations = load_json(paths.config_dir / "integrations.json")
        specialists = load_json(paths.specialist_dir / "registry.json")
    except ConfigurationError as exc:
        return [str(exc)]

    if attention.get("storage", {}).get("engine") != "sqlite":
        errors.append("storage.engine must be sqlite")
    context_ids = {item.get("id") for item in contexts.get("contexts", [])}
    if not {"inside-success", "mitchell", "personal", "mixed", "unknown"} <= context_ids:
        errors.append("required initial contexts are missing")
    if models.get("default_route") != "routine":
        errors.append("models.default_route must be routine")
    if any(item.get("mode") != "read-only" for item in integrations.get("external_sources", [])):
        errors.append("all initial external source integrations must be read-only")
    if not specialists.get("specialists"):
        errors.append("specialist registry is empty")
    return errors
