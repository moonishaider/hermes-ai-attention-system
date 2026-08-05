"""Read-only Codex history and supported ChatGPT export/context-relay ingestion."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import time
from typing import Any, Callable, Iterable, Iterator
from zipfile import ZipFile

from .domain import ConfidenceState, EvidenceItem, Provenance
from .routing import ContextRouter
from .security import detect_prompt_injection, redact_secrets
from .storage import Store


class HistoryFormatError(ValueError):
    pass


class CodexAppServerError(RuntimeError):
    """Raised when the local, read-only Codex App Server bridge fails closed."""


class CodexAppServerClient:
    """Minimal JSONL client with an immutable read-method allowlist.

    The client starts Codex over stdio for one bounded synchronization and then
    exits. It exposes only thread listing and reading methods, including the
    official experimental paginated turn-read method needed to avoid loading
    multi-megabyte full histories. It exposes no turn start, command, thread
    mutation, config write, or tool-call method.
    """

    ALLOWED_METHODS = frozenset({"thread/list", "thread/turns/list"})
    MAX_RESPONSE_BYTES = 8 * 1024 * 1024

    def __init__(self, executable: Path | str | None = None, *, timeout_seconds: float = 20.0) -> None:
        selected = str(executable) if executable is not None else shutil.which("codex")
        if not selected:
            # Finder-launched applications receive a minimal PATH. These are
            # the reviewed official macOS app/CLI locations, not a filesystem
            # search or an arbitrary executable supplied by conversation data.
            for candidate in (
                Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
                Path("/Applications/Codex.app/Contents/Resources/codex"),
                Path.home() / ".local/bin/codex",
            ):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    selected = str(candidate)
                    break
        if not selected:
            raise CodexAppServerError("Codex CLI is unavailable")
        self.executable = Path(selected).expanduser().resolve()
        if not self.executable.is_file() or not os.access(self.executable, os.X_OK):
            raise CodexAppServerError("Codex CLI executable is unavailable")
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 60.0))
        self._request_id = 0
        self._process: subprocess.Popen[str] | None = None

    def __enter__(self) -> "CodexAppServerClient":
        self._process = subprocess.Popen(
            [str(self.executable), "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        try:
            self._request_id += 1
            self._send({
                "method": "initialize",
                "id": self._request_id,
                "params": {
                    "clientInfo": {
                        "name": "hermes-attention-readonly",
                        "title": "Hermes Attention Read-Only Sync",
                        "version": "0.1.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            })
            self._receive(self._request_id)
            self._send({"method": "initialized", "params": {}})
        except Exception:
            self.__exit__()
            raise
        return self

    def __exit__(self, *_: object) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.stdin:
            process.stdin.close()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

    def _send(self, payload: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise CodexAppServerError("Codex App Server is not running")
        self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

    def _receive(self, request_id: int) -> dict[str, Any]:
        if self._process is None or self._process.stdout is None:
            raise CodexAppServerError("Codex App Server is not running")
        selector = selectors.DefaultSelector()
        selector.register(self._process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + self.timeout_seconds
        try:
            while time.monotonic() < deadline:
                remaining = max(0.0, deadline - time.monotonic())
                if not selector.select(remaining):
                    break
                line = self._process.stdout.readline(self.MAX_RESPONSE_BYTES + 1)
                if not line:
                    break
                if len(line.encode("utf-8", errors="replace")) > self.MAX_RESPONSE_BYTES:
                    raise CodexAppServerError("Codex App Server response exceeded the safety limit")
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CodexAppServerError("Codex App Server returned invalid JSON") from exc
                if payload.get("id") != request_id:
                    continue
                if payload.get("error"):
                    message = str(payload["error"].get("message", "request failed")) if isinstance(payload["error"], dict) else "request failed"
                    raise CodexAppServerError(f"Codex App Server read request failed: {message[:300]}")
                result = payload.get("result")
                if not isinstance(result, dict):
                    raise CodexAppServerError("Codex App Server returned an invalid result")
                return result
        finally:
            selector.close()
        raise CodexAppServerError("Codex App Server read request timed out")

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in self.ALLOWED_METHODS:
            raise PermissionError(f"Codex App Server method is not allowed: {method}")
        self._request_id += 1
        self._send({"method": method, "id": self._request_id, "params": params})
        return self._receive(self._request_id)

    def list_threads(self, *, cursor: str | None, limit: int, archived: bool = False) -> dict[str, Any]:
        return self._request("thread/list", {
            "cursor": cursor,
            "limit": max(1, min(limit, 100)),
            "sortKey": "updated_at",
            "sortDirection": "desc",
            "archived": archived,
        })

    def list_turns(self, thread_id: str, *, cursor: str | None, limit: int = 10) -> dict[str, Any]:
        return self._request("thread/turns/list", {
            "threadId": thread_id,
            "cursor": cursor,
            "limit": max(1, min(limit, 20)),
            "sortDirection": "desc",
            # Summary view retains user/assistant messages while omitting the
            # heavy reasoning and tool payloads Hermes must never ingest.
            "itemsView": "summary",
        })


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


def _codex_message_text(record: dict[str, Any]) -> str:
    """Extract only human/assistant conversation text, never tool output or reasoning."""
    envelope_type = record.get("type")
    if envelope_type in {"user_message", "assistant_message"}:
        return _bounded_text(record.get("content"), 12_000)
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return ""
    payload_type = payload.get("type")
    if envelope_type == "response_item" and payload_type == "message":
        role = payload.get("role")
        if role not in {"user", "assistant"}:
            return ""
        parts = payload.get("content")
        if not isinstance(parts, list):
            return ""
        return "\n".join(
            str(part.get("text", ""))
            for part in parts
            if isinstance(part, dict) and part.get("type") in {"input_text", "output_text"}
        )[:12_000]
    if envelope_type == "event_msg" and payload_type in {"user_message", "agent_message"}:
        return _bounded_text(payload.get("message"), 12_000)
    return ""


def _record_timestamp(record: dict[str, Any]) -> datetime | None:
    value = record.get("timestamp") or record.get("created_at") or record.get("time")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, UTC)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _codex_workspace(path: Path) -> str | None:
    """Read only the early session metadata needed for deterministic context routing."""
    for index, (_, record) in enumerate(iter_jsonl(path)):
        payload = record.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("cwd"), str):
            return payload["cwd"][:2_000]
        if index >= 49:
            break
    return None


class CodexHistoryBridge:
    def __init__(self, store: Store, router: ContextRouter, codex_home: Path | None = None) -> None:
        self.store = store
        self.router = router
        self.codex_home = (codex_home or discover_codex_home()).resolve()

    def preview(self, *, start_date: str = "2026-03-01") -> dict[str, Any]:
        files = codex_history_candidates(self.codex_home)
        return {
            "codex_home": str(self.codex_home),
            "files": len(files),
            "bytes": sum(path.stat().st_size for path in files),
            "start_date": start_date,
            "read_only": True,
        }

    def ingest(self, *, maximum_records: int = 500, start_date: str = "2026-03-01") -> dict[str, int | str]:
        inserted = duplicate = scanned = 0
        threshold = datetime.fromisoformat(start_date).replace(tzinfo=UTC)
        for path in codex_history_candidates(self.codex_home):
            source_key = f"codex:{path.relative_to(self.codex_home)}"
            workspace = _codex_workspace(path)
            start_line = int(self.store.get_checkpoint(source_key) or 0)
            final_line = start_line
            for line_number, record in iter_jsonl(path, start_line=start_line):
                if scanned >= maximum_records:
                    break
                final_line = line_number + 1
                scanned += 1
                record_time = _record_timestamp(record)
                if record_time and record_time < threshold:
                    if scanned >= maximum_records:
                        break
                    continue
                text, _ = redact_secrets(_codex_message_text(record))
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
                    workspace=workspace,
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
                    confidence_state=ConfidenceState.UNCERTAIN if detect_prompt_injection(text) else ConfidenceState.INFERRED,
                )
                if self.store.add_evidence(item):
                    inserted += 1
                else:
                    duplicate += 1
            self.store.set_checkpoint(source_key, str(final_line))
            if scanned >= maximum_records:
                break
        return {"scanned": scanned, "inserted": inserted, "duplicates": duplicate, "start_date": start_date}


def _epoch_seconds(value: Any) -> int:
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, str) and value:
        try:
            return max(0, int(float(value)))
        except ValueError:
            try:
                return max(0, int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()))
            except ValueError:
                return 0
    return 0


def _iso_from_epoch(value: Any) -> str:
    seconds = _epoch_seconds(value)
    return datetime.fromtimestamp(seconds, UTC).isoformat() if seconds else datetime.now(UTC).isoformat()


def _app_server_item_text(item: dict[str, Any]) -> tuple[str, str]:
    """Return role and text for user/final-or-progress assistant messages only."""
    item_type = item.get("type")
    if item_type == "userMessage":
        content = item.get("content")
        if not isinstance(content, list):
            return "", ""
        text = "\n".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
        return "user", text[:12_000]
    if item_type == "agentMessage" and isinstance(item.get("text"), str):
        return "assistant", item["text"][:12_000]
    # Reasoning, tool calls/results, commands, patches, images, and plans are
    # deliberately not imported as conversational evidence.
    return "", ""


class CodexAppServerBridge:
    """Incrementally ingest current Codex conversations through official reads."""

    GLOBAL_CHECKPOINT = "codex-app-server:updated-at"

    def __init__(
        self,
        store: Store,
        router: ContextRouter,
        *,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.store = store
        self.router = router
        self.client_factory = client_factory or CodexAppServerClient

    def sync(
        self,
        *,
        lookback_days: int = 14,
        maximum_threads: int = 50,
        maximum_items: int = 2_000,
    ) -> dict[str, Any]:
        started = time.monotonic()
        lookback_days = max(1, min(int(lookback_days), 90))
        maximum_threads = max(1, min(int(maximum_threads), 100))
        maximum_items = max(1, min(int(maximum_items), 5_000))
        lookback_epoch = int(datetime.now(UTC).timestamp()) - lookback_days * 86_400
        saved_global = _epoch_seconds(self.store.get_checkpoint(self.GLOBAL_CHECKPOINT))
        cutoff = max(lookback_epoch, saved_global)
        thread_summaries: list[dict[str, Any]] = []
        cursor: str | None = None
        pages = 0

        with self.client_factory() as client:
            while len(thread_summaries) < maximum_threads:
                page = client.list_threads(
                    cursor=cursor,
                    limit=min(50, maximum_threads - len(thread_summaries)),
                    archived=False,
                )
                pages += 1
                values = page.get("data")
                if not isinstance(values, list):
                    raise CodexAppServerError("Codex thread listing returned invalid data")
                reached_cutoff = False
                for value in values:
                    if not isinstance(value, dict):
                        continue
                    updated_at = _epoch_seconds(value.get("updatedAt"))
                    if updated_at < cutoff:
                        reached_cutoff = True
                        break
                    if isinstance(value.get("id"), str) and value["id"]:
                        thread_summaries.append(value)
                    if len(thread_summaries) >= maximum_threads:
                        break
                cursor_value = page.get("nextCursor")
                cursor = cursor_value if isinstance(cursor_value, str) and cursor_value else None
                if reached_cutoff or not cursor or not values:
                    break

            inserted = duplicates = items_scanned = turns_scanned = threads_read = redactions = injection_flags = 0
            newest_updated_at = saved_global
            for summary in thread_summaries:
                if items_scanned >= maximum_items:
                    break
                thread_id = summary["id"]
                updated_at = _epoch_seconds(summary.get("updatedAt"))
                newest_updated_at = max(newest_updated_at, updated_at)
                thread_checkpoint = f"codex-app-server:thread:{thread_id}"
                prior_turn_id = self.store.get_checkpoint(thread_checkpoint)
                turn_cursor: str | None = None
                completed_turns: list[dict[str, Any]] = []
                newest_turn_id = ""
                reached_prior = False
                while (
                    len(completed_turns) < 20
                    and items_scanned + sum(len(turn.get("items") or []) for turn in completed_turns) < maximum_items
                ):
                    # Summary pages retain user/assistant text but omit heavy
                    # reasoning and tool payloads, so ten turns remain bounded.
                    turn_page = client.list_turns(thread_id, cursor=turn_cursor, limit=10)
                    turn_values = turn_page.get("data")
                    if not isinstance(turn_values, list):
                        raise CodexAppServerError("Codex turn listing returned invalid data")
                    if not turn_values:
                        break
                    for turn in turn_values:
                        if not isinstance(turn, dict):
                            continue
                        turn_id = str(turn.get("id") or "")
                        if prior_turn_id and turn_id == prior_turn_id:
                            reached_prior = True
                            break
                        if turn.get("status") not in {"completed", "interrupted", "failed"}:
                            continue
                        turn_epoch = _epoch_seconds(turn.get("completedAt") or turn.get("startedAt"))
                        if turn_epoch and turn_epoch < lookback_epoch:
                            reached_prior = True
                            break
                        if turn_id and not newest_turn_id:
                            newest_turn_id = turn_id
                        completed_turns.append(turn)
                    next_cursor = turn_page.get("nextCursor")
                    turn_cursor = next_cursor if isinstance(next_cursor, str) and next_cursor else None
                    if reached_prior or not turn_cursor:
                        break
                if not completed_turns:
                    continue
                threads_read += 1
                turns_scanned += len(completed_turns)
                workspace = str(summary.get("cwd") or "")[:2_000] or None
                title = str(summary.get("name") or "Codex conversation")[:300]
                selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
                for turn in completed_turns:
                    turn_items = turn.get("items")
                    if not isinstance(turn_items, list):
                        continue
                    for item in turn_items:
                        if isinstance(item, dict):
                            role, text = _app_server_item_text(item)
                            if role and text:
                                selected.append((turn, item))
                                if items_scanned + len(selected) >= maximum_items:
                                    break
                    if items_scanned + len(selected) >= maximum_items:
                        break
                for turn, item in reversed(selected):
                    role, raw_text = _app_server_item_text(item)
                    text, found_redactions = redact_secrets(raw_text)
                    redactions += found_redactions
                    flags = detect_prompt_injection(text)
                    injection_flags += len(flags)
                    turn_id = str(turn.get("id") or "unknown-turn")
                    item_id = str(item.get("id") or sha256(raw_text.encode()).hexdigest()[:24])
                    source_id = f"{thread_id}:{turn_id}:{item_id}"
                    timestamp = _iso_from_epoch(turn.get("completedAt") or turn.get("startedAt") or updated_at)
                    provenance = Provenance(
                        source_system="codex",
                        connection_id="codex_app_server_readonly",
                        source_id=source_id,
                        source_timestamp=timestamp,
                        retrieved_at=datetime.now(UTC).isoformat(),
                        account_id="local-codex",
                        workspace=workspace,
                        container=thread_id,
                        uri=f"codex://thread/{thread_id}/turn/{turn_id}/item/{item_id}",
                        revision=sha256(json.dumps(item, sort_keys=True, default=str).encode()).hexdigest(),
                        permission_ref="app-server-readonly:thread-list,thread-turns-list",
                    )
                    contexts = self.router.classify(provenance)
                    evidence = EvidenceItem(
                        evidence_id=f"codex-app-server:{sha256(source_id.encode()).hexdigest()}",
                        title=f"{title} — {role}",
                        content=text,
                        provenance=provenance,
                        contexts=contexts,
                        confidence_state=ConfidenceState.UNCERTAIN if flags else ConfidenceState.INFERRED,
                    )
                    if self.store.add_evidence(evidence):
                        inserted += 1
                    else:
                        duplicates += 1
                    items_scanned += 1
                if newest_turn_id:
                    self.store.set_checkpoint(thread_checkpoint, newest_turn_id)

        if newest_updated_at:
            self.store.set_checkpoint(self.GLOBAL_CHECKPOINT, str(newest_updated_at))
        result = {
            "ok": True,
            "transport": "stdio",
            "read_methods": ["thread/list", "thread/turns/list"],
            "thread_turns_list_status": "official-experimental-bounded-pagination",
            "pages": pages,
            "threads_considered": len(thread_summaries),
            "threads_read": threads_read,
            "turns_scanned": turns_scanned,
            "items_scanned": items_scanned,
            "inserted": inserted,
            "duplicates": duplicates,
            "secret_redactions": redactions,
            "prompt_injection_flags": injection_flags,
            "lookback_days": lookback_days,
            "checkpoint": _iso_from_epoch(newest_updated_at) if newest_updated_at else None,
            "duration_ms": int((time.monotonic() - started) * 1_000),
            "external_writes": False,
            "thread_mutations": False,
        }
        self.store.audit("codex-sync", "codex.app-server.read", None, "success", result)
        return result


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
    MAX_CONVERSATION_BYTES = 512 * 1024 * 1024

    def __init__(self, store: Store, router: ContextRouter) -> None:
        self.store = store
        self.router = router

    @staticmethod
    def load(path: Path) -> list[dict[str, Any]]:
        if path.suffix.casefold() == ".zip":
            with ZipFile(path) as archive:
                infos = archive.infolist()
                single = [info for info in infos if Path(info.filename).name == "conversations.json"]
                shards = [info for info in infos if re.fullmatch(r"conversations-\d{3}\.json", Path(info.filename).name)]
                if single and shards:
                    raise HistoryFormatError("export ZIP cannot mix conversations.json with conversation shards")
                if len(single) == 1:
                    selected = single
                elif not single and shards:
                    selected = sorted(shards, key=lambda info: Path(info.filename).name)
                    expected = [f"conversations-{index:03d}.json" for index in range(len(selected))]
                    actual = [Path(info.filename).name for info in selected]
                    if actual != expected:
                        raise HistoryFormatError("export ZIP conversation shards must be unique and contiguous from 000")
                else:
                    raise HistoryFormatError("export ZIP must contain one conversations.json or contiguous conversations-NNN.json shards")
                if any(info.flag_bits & 1 for info in selected):
                    raise HistoryFormatError("encrypted conversation entries are unsupported")
                if sum(info.file_size for info in selected) > ChatGPTExportImporter.MAX_CONVERSATION_BYTES:
                    raise HistoryFormatError("export conversation data exceeds the bounded import limit")
                payload = []
                for info in selected:
                    shard = json.loads(archive.read(info))
                    payload.extend(iter_chatgpt_conversations(shard))
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
            content, _ = redact_secrets("\n\n".join(message for message in messages if message)[:100_000])
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
            revision = sha256(content.encode()).hexdigest()
            evidence_id = f"chatgpt:{conversation_id}:{revision[:16]}"
            if self.store.connection.execute(
                "SELECT 1 FROM evidence WHERE evidence_id=?", (evidence_id,)
            ).fetchone():
                duplicate += 1
                continue
            item = EvidenceItem(
                evidence_id=evidence_id,
                title=str(conversation.get("title") or "ChatGPT conversation"),
                content=content,
                provenance=provenance,
                contexts=self.router.classify(provenance),
                confidence_state=ConfidenceState.UNCERTAIN if detect_prompt_injection(content) else ConfidenceState.INFERRED,
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
        content, _ = redact_secrets("\n\n".join(
            str(payload.get(field, ""))
            for field in ("summary", "decisions", "commitments", "unresolved_questions", "selected_excerpts")
            if payload.get(field)
        ))
        item = EvidenceItem(
            evidence_id=f"chatgpt-relay:{relay_id}",
            title=str(payload["title"]),
            content=content,
            provenance=provenance,
            contexts=self.router.classify(provenance, hints=tuple(payload["context_labels"])),
            confidence_state=ConfidenceState.UNCERTAIN if detect_prompt_injection(content) else ConfidenceState.INFERRED,
        )
        return self.store.add_evidence(item)
