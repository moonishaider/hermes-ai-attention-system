"""Read-only Codex history and supported ChatGPT export/context-relay ingestion."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable, Iterator
from zipfile import ZipFile

from .domain import EvidenceItem, Provenance
from .routing import ContextRouter
from .storage import Store


class HistoryFormatError(ValueError):
    pass


def discover_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    candidate = Path(configured).expanduser() if configured else Path.home() / ".codex"
    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise HistoryFormatError(f"Codex home is unavailable: {resolved}")
    return resolved


def codex_history_candidates(codex_home: Path) -> list[Path]:
    candidates: list[Path] = []
    history = codex_home / "history.jsonl"
    if history.is_file():
        candidates.append(history)
    for directory_name in ("sessions", "archived_sessions"):
        directory = codex_home / directory_name
        if not directory.is_dir():
            continue
        candidates.extend(sorted(p for p in directory.rglob("*.jsonl") if p.is_file()))
    return candidates


def iter_jsonl(path: Path, *, start_line: int = 0) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle):
            if line_number < start_line or not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield line_number, value


def _bounded_text(value: Any, limit: int = 12_000) -> str:
    if isinstance(value, str):
        return value[:limit]
    if isinstance(value, list):
        return "\n".join(_bounded_text(item, limit) for item in value)[:limit]
    if isinstance(value, dict):
        for key in ("text", "content", "message", "prompt", "summary"):
            if key in value:
                return _bounded_text(value[key], limit)
    return ""


class CodexHistoryBridge:
    def __init__(self, store: Store, router: ContextRouter, codex_home: Path | None = None) -> None:
        self.store = store
        self.router = router
        self.codex_home = (codex_home or discover_codex_home()).resolve()

    def preview(self) -> dict[str, Any]:
        files = codex_history_candidates(self.codex_home)
        return {
            "codex_home": str(self.codex_home),
            "files": len(files),
            "bytes": sum(path.stat().st_size for path in files),
            "read_only": True,
        }

    def ingest(self, *, maximum_records: int = 500) -> dict[str, int]:
        inserted = duplicate = scanned = 0
        for path in codex_history_candidates(self.codex_home):
            source_key = f"codex:{path.relative_to(self.codex_home)}"
            start_line = int(self.store.get_checkpoint(source_key) or 0)
            final_line = start_line
            for line_number, record in iter_jsonl(path, start_line=start_line):
                final_line = line_number + 1
                scanned += 1
                text = _bounded_text(record)
                if not text:
                    continue
                timestamp = str(record.get("timestamp") or record.get("created_at") or datetime.now(UTC).isoformat())
                record_id = str(record.get("id") or record.get("session_id") or f"{path.name}:{line_number}")
                provenance = Provenance(
                    source_system="codex",
                    connection_id="codex_local_readonly",
                    source_id=record_id,
                    source_timestamp=timestamp,
                    retrieved_at=datetime.now(UTC).isoformat(),
                    account_id="local-codex",
                    container=str(path.relative_to(self.codex_home)),
                    uri=f"codex://{path.relative_to(self.codex_home)}#{line_number + 1}",
                    revision=sha256(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest(),
                    permission_ref="local-readonly",
                )
                contexts = self.router.classify(provenance, hints=tuple(record.get("contexts", [])))
                item = EvidenceItem(
                    evidence_id=f"codex:{sha256((source_key + ':' + record_id).encode()).hexdigest()}",
                    title=str(record.get("title") or record.get("type") or "Codex history event"),
                    content=text,
                    provenance=provenance,
                    contexts=contexts,
                )
                if self.store.add_evidence(item):
                    inserted += 1
                else:
                    duplicate += 1
                if scanned >= maximum_records:
                    break
            self.store.set_checkpoint(source_key, str(final_line))
            if scanned >= maximum_records:
                break
        return {"scanned": scanned, "inserted": inserted, "duplicates": duplicate}


def _chatgpt_message_text(node: dict[str, Any]) -> str:
    message = node.get("message") or {}
    content = message.get("content") or {}
    parts = content.get("parts") or []
    return "\n".join(str(part) for part in parts if isinstance(part, (str, int, float)))


def iter_chatgpt_conversations(payload: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(payload, list):
        raise HistoryFormatError("ChatGPT conversations.json must contain a list")
    for conversation in payload:
        if isinstance(conversation, dict):
            yield conversation


class ChatGPTExportImporter:
    def __init__(self, store: Store, router: ContextRouter) -> None:
        self.store = store
        self.router = router

    @staticmethod
    def load(path: Path) -> list[dict[str, Any]]:
        if path.suffix.casefold() == ".zip":
            with ZipFile(path) as archive:
                names = [name for name in archive.namelist() if Path(name).name == "conversations.json"]
                if len(names) != 1:
                    raise HistoryFormatError("export ZIP must contain exactly one conversations.json")
                payload = json.loads(archive.read(names[0]))
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
        return list(iter_chatgpt_conversations(payload))

    def preview(self, path: Path, *, start_date: str) -> dict[str, Any]:
        conversations = self.load(path)
        threshold = datetime.fromisoformat(start_date).replace(tzinfo=UTC).timestamp()
        selected = [item for item in conversations if float(item.get("create_time") or 0) >= threshold]
        return {
            "source": str(path),
            "conversations_total": len(conversations),
            "conversations_selected": len(selected),
            "start_date": start_date,
            "requires_confirmation": True,
        }

    def ingest(self, path: Path, *, start_date: str, confirmed: bool = False) -> dict[str, int]:
        if not confirmed:
            raise PermissionError("ChatGPT import requires explicit confirmation after preview")
        threshold = datetime.fromisoformat(start_date).replace(tzinfo=UTC).timestamp()
        inserted = duplicate = 0
        for conversation in self.load(path):
            created = float(conversation.get("create_time") or 0)
            if created < threshold:
                continue
            conversation_id = str(conversation.get("id") or conversation.get("conversation_id") or "unknown")
            messages = [_chatgpt_message_text(node) for node in (conversation.get("mapping") or {}).values()]
            content = "\n\n".join(message for message in messages if message)[:100_000]
            if not content:
                continue
            timestamp = datetime.fromtimestamp(created, UTC).isoformat()
            provenance = Provenance(
                source_system="chatgpt_export",
                connection_id="chatgpt_official_export",
                source_id=conversation_id,
                source_timestamp=timestamp,
                retrieved_at=datetime.now(UTC).isoformat(),
                account_id="user-export",
                container="conversations.json",
                uri=f"chatgpt-export://{conversation_id}",
                revision=sha256(content.encode()).hexdigest(),
                permission_ref="owner-provided-export",
            )
            item = EvidenceItem(
                evidence_id=f"chatgpt:{conversation_id}",
                title=str(conversation.get("title") or "ChatGPT conversation"),
                content=content,
                provenance=provenance,
                contexts=self.router.classify(provenance),
            )
            if self.store.add_evidence(item):
                inserted += 1
            else:
                duplicate += 1
        return {"inserted": inserted, "duplicates": duplicate}


class ContextRelayImporter:
    REQUIRED_FIELDS = {"title", "date", "summary", "context_labels", "source_reference"}

    def __init__(self, store: Store, router: ContextRouter) -> None:
        self.store = store
        self.router = router

    def ingest(self, path: Path) -> bool:
        payload = json.loads(path.read_text(encoding="utf-8"))
        missing = self.REQUIRED_FIELDS - payload.keys()
        if missing:
            raise HistoryFormatError(f"context relay is missing: {', '.join(sorted(missing))}")
        relay_id = sha256(str(payload["source_reference"]).encode()).hexdigest()
        provenance = Provenance(
            source_system="chatgpt_context_relay",
            connection_id="chatgpt_explicit_relay",
            source_id=relay_id,
            source_timestamp=str(payload["date"]),
            retrieved_at=datetime.now(UTC).isoformat(),
            account_id="user-explicit",
            container=path.name,
            uri=str(payload["source_reference"]),
            revision=sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            permission_ref="explicit-context-relay",
        )
        content = "\n\n".join(
            str(payload.get(field, ""))
            for field in ("summary", "decisions", "commitments", "unresolved_questions", "selected_excerpts")
            if payload.get(field)
        )
        item = EvidenceItem(
            evidence_id=f"chatgpt-relay:{relay_id}",
            title=str(payload["title"]),
            content=content,
            provenance=provenance,
            contexts=self.router.classify(provenance, hints=tuple(payload["context_labels"])),
        )
        return self.store.add_evidence(item)
