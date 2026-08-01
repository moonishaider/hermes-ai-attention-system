"""Non-echoing, resumable Hermes secret setup outside Git."""

from __future__ import annotations

import getpass
import os
from pathlib import Path
import tempfile


ALLOWED_KEYS = {"DEEPSEEK_API_KEY", "OPENAI_API_KEY"}


def configured_keys(env_path: Path | None = None) -> dict[str, bool]:
    path = env_path or Path.home() / ".hermes" / ".env"
    present = set()
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                if value.strip():
                    present.add(key.strip())
    return {key: key in os.environ or key in present for key in sorted(ALLOWED_KEYS)}


def prompt_and_store(key_name: str, env_path: Path | None = None) -> None:
    if key_name not in ALLOWED_KEYS:
        raise ValueError("secret name is not allowlisted")
    path = env_path or Path.home() / ".hermes" / ".env"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    value = getpass.getpass(f"Enter {key_name} (input hidden): ").strip()
    if not value or "\n" in value or "\r" in value:
        raise ValueError("secret was empty or malformed")
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    replacement = f"{key_name}={value}"
    output = []
    replaced = False
    for line in lines:
        if line.split("=", 1)[0].strip() == key_name and not line.lstrip().startswith("#"):
            output.append(replacement)
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(replacement)
    handle, temporary = tempfile.mkstemp(prefix=".env.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write("\n".join(output) + "\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
