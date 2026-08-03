"""Fail-closed local control channel for the foreground Hermes overlay."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
from typing import Callable, Iterable


_ALLOWED_CONTROLS = frozenset({"approve", "cancel", "dismiss", "mute", "unmute"})
_AUDIO_PLAYERS = frozenset({"afplay", "ffplay"})


@dataclass(frozen=True, slots=True)
class OverlayControlEvent:
    control: str
    preview_hash: str | None = None

    def __post_init__(self) -> None:
        if self.control not in _ALLOWED_CONTROLS:
            raise ValueError("unsupported overlay control")
        if self.control == "approve" and not self.preview_hash:
            raise ValueError("approve requires the exact visible preview hash")

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


@dataclass(frozen=True, slots=True)
class ProcessRecord:
    pid: int
    parent_pid: int
    command: str


def _secure_fifo(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISFIFO(info.st_mode):
        raise ValueError("overlay control path must be a FIFO")
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise PermissionError("overlay control FIFO must be owner-only")


def send_control(path: Path, event: OverlayControlEvent) -> None:
    """Write one bounded control event to an owner-only launcher FIFO."""
    _secure_fifo(path)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(event.to_json() + "\n")


def process_snapshot() -> list[ProcessRecord]:
    result = subprocess.run(
        ["/bin/ps", "-axo", "pid=,ppid=,command="],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    records: list[ProcessRecord] = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(maxsplit=2)
        if len(fields) != 3:
            continue
        try:
            records.append(ProcessRecord(int(fields[0]), int(fields[1]), fields[2]))
        except ValueError:
            continue
    return records


class OverlayControlSupervisor:
    """Apply only mute/cancel controls to this launcher's exact Hermes child."""

    def __init__(
        self,
        *,
        launcher_pid: int,
        expected_hermes_path: Path,
        mute_state_path: Path,
        audit_path: Path,
        snapshot: Callable[[], list[ProcessRecord]] = process_snapshot,
        signal_process: Callable[[int, int], None] = os.kill,
    ) -> None:
        self.launcher_pid = launcher_pid
        self.expected_hermes_path = str(expected_hermes_path.resolve())
        self.mute_state_path = mute_state_path
        self.audit_path = audit_path
        self.snapshot = snapshot
        self.signal_process = signal_process
        self._state = {"muted": False, "cancel_sequence": 0}
        self._write_mute_state(False)

    def _write_private_json(self, path: Path, payload: dict[str, object], *, append: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else os.O_TRUNC)
        descriptor = os.open(path, flags, 0o600)
        try:
            with os.fdopen(descriptor, "a" if append else "w", encoding="utf-8") as stream:
                stream.write(json.dumps(payload, sort_keys=True) + "\n")
        finally:
            try:
                os.chmod(path, 0o600)
            except FileNotFoundError:
                pass

    def _write_mute_state(self, muted: bool) -> None:
        self._state["muted"] = muted
        self._write_private_json(self.mute_state_path, self._state)

    def _hermes_pid(self, records: Iterable[ProcessRecord]) -> int | None:
        matches = [
            item.pid
            for item in records
            if item.parent_pid == self.launcher_pid
            and self.expected_hermes_path in item.command.split()[:3]
        ]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _descendants(root_pid: int, records: Iterable[ProcessRecord]) -> set[int]:
        rows = tuple(records)
        found: set[int] = set()
        frontier = {root_pid}
        while frontier:
            children = {item.pid for item in rows if item.parent_pid in frontier and item.pid not in found}
            found.update(children)
            frontier = children
        return found

    def _stop_exact_audio_descendants(self, hermes_pid: int, records: Iterable[ProcessRecord]) -> int:
        rows = tuple(records)
        descendants = self._descendants(hermes_pid, rows)
        stopped = 0
        for item in rows:
            executable = Path(item.command.split(maxsplit=1)[0]).name
            if item.pid in descendants and executable in _AUDIO_PLAYERS:
                self.signal_process(item.pid, signal.SIGTERM)
                stopped += 1
        return stopped

    def handle(self, event: OverlayControlEvent) -> dict[str, object]:
        records = self.snapshot()
        hermes_pid = self._hermes_pid(records)
        result: dict[str, object] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "control": event.control,
            "applied": False,
            "reason": "no exact foreground Hermes child",
        }
        if event.control == "dismiss":
            result.update(applied=True, reason="overlay hidden locally")
        elif event.control == "approve":
            result.update(applied=False, reason="approval recorded only; no executor is exposed", preview_hash=event.preview_hash)
        elif hermes_pid is not None and event.control == "cancel":
            self._state["cancel_sequence"] = int(self._state["cancel_sequence"]) + 1
            self._write_private_json(self.mute_state_path, self._state)
            result.update(applied=True, reason="cancel queued to trusted Hermes plugin bridge", hermes_pid=hermes_pid)
        elif hermes_pid is not None and event.control in {"mute", "unmute"}:
            muted = event.control == "mute"
            self._write_mute_state(muted)
            stopped = self._stop_exact_audio_descendants(hermes_pid, records) if muted else 0
            result.update(applied=True, reason="project voice output state updated", muted=muted, stopped_players=stopped, hermes_pid=hermes_pid)
        self._write_private_json(self.audit_path, result, append=True)
        return result

    def run(self, control_fifo: Path) -> None:
        _secure_fifo(control_fifo)
        while True:
            with control_fifo.open("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        payload = json.loads(line)
                        self.handle(OverlayControlEvent(
                            control=str(payload.get("control", "")),
                            preview_hash=payload.get("preview_hash"),
                        ))
                    except (ValueError, TypeError, json.JSONDecodeError) as exc:
                        self._write_private_json(self.audit_path, {
                            "at": datetime.now(timezone.utc).isoformat(),
                            "control": "invalid",
                            "applied": False,
                            "reason": type(exc).__name__,
                        }, append=True)
