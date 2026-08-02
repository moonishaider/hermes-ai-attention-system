"""Resumable automation-first onboarding state and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .config import ProjectPaths, load_json, validate_project_configuration
from .history import ChatGPTExportImporter, CodexHistoryBridge
from .runtime_models import DirectModelClient
from .secrets import configured_keys
from .service import AttentionService


@dataclass(frozen=True, slots=True)
class StepResult:
    step: str
    state: str
    detail: str
    checked_at: str


def summarize_connectors(integrations: dict[str, Any]) -> tuple[str, str]:
    """Return a credential-safe registry summary without claiming live OAuth health."""
    sources = integrations.get("external_sources", [])
    remote = [item for item in sources if item.get("type") not in {"local-jsonl", "official-export"}]
    enabled = sorted(str(item.get("id")) for item in remote if item.get("enabled") is True)
    pending = sorted(str(item.get("id")) for item in remote if item.get("enabled") is not True)
    detail = f"registry_enabled={len(enabled)}/{len(remote)}"
    if enabled:
        detail += "; enabled=" + ",".join(enabled)
    if pending:
        detail += "; pending=" + ",".join(pending)
    detail += "; live health remains subject to per-connector smoke tests"
    return ("complete" if remote and not pending else "human_required"), detail


class OnboardingOrchestrator:
    STEPS = ("project", "hermes", "plugin", "voice", "microphone_permission", "history", "chatgpt_export", "model_secrets", "model_smokes", "connectors", "screen_permission", "final")

    def __init__(self, paths: ProjectPaths | None = None) -> None:
        self.paths = paths or ProjectPaths.discover()
        self.state_path = self.paths.runtime_dir / "onboarding-status.json"
        self.paths.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return {"schema_version": 2, "steps": {}}
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                value["schema_version"] = 2
                return value
            return {"schema_version": 2, "steps": {}}
        except json.JSONDecodeError:
            return {"schema_version": 2, "steps": {}}

    def _record(self, step: str, state: str, detail: str) -> StepResult:
        result = StepResult(step, state, detail, datetime.now(UTC).isoformat())
        self.state.setdefault("steps", {})[step] = asdict(result)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.state_path)
        return result

    def run(
        self, *, history_batch: int = 500, start_date: str = "2026-03-01",
        chatgpt_export: Path | None = None, confirm_chatgpt_import: bool = False,
    ) -> dict[str, Any]:
        results = []
        errors = validate_project_configuration(self.paths)
        results.append(self._record("project", "complete" if not errors else "failed", "configuration valid" if not errors else "; ".join(errors)))

        hermes = Path.home() / ".local" / "bin" / "hermes"
        results.append(self._record("hermes", "complete" if hermes.is_file() else "failed", str(hermes)))
        plugin = self.paths.root / ".hermes/plugins/hermes-attention/plugin.yaml"
        launcher = self.paths.root / "scripts/launch_hermes.sh"
        enabled = plugin.is_file() and launcher.is_file() and "HERMES_ENABLE_PROJECT_PLUGINS=1" in launcher.read_text(encoding="utf-8")
        results.append(self._record("plugin", "complete" if enabled else "failed", "project plugin is enabled only by guarded launcher" if enabled else "project plugin launcher is incomplete"))

        # The installed Hermes launcher executes ``hermes-agent/venv``.  A
        # source checkout may also contain ``.venv``, but validating that
        # unused environment would produce a false operational success.
        python = Path.home() / ".hermes/hermes-agent/venv/bin/python"
        voice_ok = False
        if python.is_file():
            check = subprocess.run([str(python), "-c", "import sounddevice, faster_whisper, edge_tts, pvporcupine"], capture_output=True, text=True)
            voice_ok = check.returncode == 0
        results.append(self._record("voice", "complete" if voice_ok else "failed", "voice, TTS, and wake dependencies import" if voice_ok else "voice dependency import failed"))
        results.append(self._record("microphone_permission", "human_required", "voice dependencies are ready; macOS Microphone permission has not been requested"))

        service = AttentionService(paths=self.paths)
        chatgpt_detail = "official export not selected"
        try:
            history = CodexHistoryBridge(service.store, service.router).ingest(maximum_records=history_batch, start_date=start_date)
            if chatgpt_export:
                importer = ChatGPTExportImporter(service.store, service.router)
                preview = importer.preview(chatgpt_export, start_date=start_date)
                chatgpt_detail = f"preview selected={preview['conversations_selected']} total={preview['conversations_total']}"
                if confirm_chatgpt_import:
                    imported = importer.ingest(chatgpt_export, start_date=start_date, confirmed=True)
                    chatgpt_detail += f" imported={imported['inserted']} duplicates={imported['duplicates']}"
        except Exception:
            service.close()
            raise
        results.append(self._record("history", "complete", f"Codex bounded batch scanned={history['scanned']} inserted={history['inserted']} start={start_date}"))
        chatgpt_state = "complete" if chatgpt_export else "human_required"
        results.append(self._record("chatgpt_export", chatgpt_state, f"ChatGPT {chatgpt_detail}; explicit context relay remains available"))

        keys = configured_keys()
        provider_keys = {name: keys[name] for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY")}
        results.append(self._record("model_secrets", "complete" if all(provider_keys.values()) else "human_required", "configured=" + ",".join(key for key, present in provider_keys.items() if present) + "; missing=" + ",".join(key for key, present in provider_keys.items() if not present)))
        smoke_results = []
        client = DirectModelClient(self.paths.config_dir / "models.json", service.store)
        synthetic_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        for route, required_key in (("routine", "DEEPSEEK_API_KEY"), ("difficult", "DEEPSEEK_API_KEY"), ("vision", "OPENAI_API_KEY"), ("review", "OPENAI_API_KEY")):
            if keys[required_key]:
                smoke_results.append(client.smoke(route, image_data_url=synthetic_image if route == "vision" else None))
        service.close()
        smokes_complete = len(smoke_results) == 4 and all(item["success"] for item in smoke_results)
        results.append(self._record("model_smokes", "complete" if smokes_complete else ("failed" if smoke_results and any(not item["success"] for item in smoke_results) else "blocked"), json.dumps(smoke_results, sort_keys=True)))
        connector_state, connector_detail = summarize_connectors(load_json(self.paths.config_dir / "integrations.json"))
        results.append(self._record("connectors", connector_state, connector_detail))
        results.append(self._record("screen_permission", "human_required", "one-shot adapter ready; macOS permission not requested"))
        pending = [item.step for item in results if item.state in {"human_required", "blocked", "failed"}]
        results.append(self._record("final", "complete" if not pending else "blocked", "all onboarding steps complete" if not pending else "pending=" + ",".join(pending)))
        return {"complete": not pending, "resumable": True, "state_path": str(self.state_path), "results": [asdict(item) for item in results]}

    def status(self) -> dict[str, Any]:
        return {"resumable": True, "state_path": str(self.state_path), **self.state}
