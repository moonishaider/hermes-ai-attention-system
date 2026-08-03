"""Lightweight local transcript/status overlay contract and optional Tk UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
from typing import Callable

from .overlay_control import OverlayControlEvent, send_control


@dataclass(frozen=True, slots=True)
class OverlayEvent:
    state: str
    transcript: str = ""
    status: str = ""
    response: str = ""
    context: str = "unknown"
    source: str = ""
    proposal_id: str | None = None
    preview_hash: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class OverlayEventBus:
    def __init__(self) -> None:
        self._subscribers: list[Callable[[OverlayEvent], None]] = []

    def subscribe(self, callback: Callable[[OverlayEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: OverlayEvent) -> None:
        for callback in tuple(self._subscribers):
            callback(event)


def run_tk_overlay() -> int:
    """Read JSON events from stdin and display them; never captures the screen."""
    import tkinter as tk

    root = tk.Tk()
    root.title("Hermes Attention")
    root.attributes("-topmost", True)
    root.geometry("560x230+40+40")
    root.configure(bg="#111827")

    transcript = tk.StringVar(value="Listening is off")
    status = tk.StringVar(value="Idle")
    response = tk.StringVar(value="")
    context = tk.StringVar(value="unknown")
    control_path_value = os.environ.get("HERMES_ATTENTION_OVERLAY_CONTROL_FIFO", "")
    control_path = Path(control_path_value) if control_path_value else None
    muted = tk.BooleanVar(value=False)
    visible_preview_hash: str | None = None

    for variable, size, color in (
        (transcript, 12, "#d1d5db"),
        (status, 10, "#93c5fd"),
        (response, 12, "#f9fafb"),
        (context, 9, "#a7f3d0"),
    ):
        tk.Label(root, textvariable=variable, font=("Helvetica", size), fg=color, bg="#111827", wraplength=520, justify="left").pack(anchor="w", padx=16, pady=4)

    def emit_control(control: str) -> None:
        nonlocal visible_preview_hash
        try:
            event = OverlayControlEvent(
                control=control,
                preview_hash=visible_preview_hash if control == "approve" else None,
            )
            if control_path is None:
                print(event.to_json(), flush=True)
            else:
                send_control(control_path, event)
        except (OSError, ValueError, PermissionError):
            status.set("Control channel unavailable; nothing was changed")

    def toggle_mute() -> None:
        next_value = not muted.get()
        muted.set(next_value)
        mute_button.configure(text="Unmute Voice" if next_value else "Mute Voice")
        status.set("Voice output muted" if next_value else "Voice output enabled")
        emit_control("mute" if next_value else "unmute")

    def dismiss() -> None:
        emit_control("dismiss")
        root.withdraw()

    controls = tk.Frame(root, bg="#111827")
    controls.pack(fill="x", padx=16, pady=8)
    approve_button = tk.Button(controls, text="Approve", state="disabled", command=lambda: emit_control("approve"))
    approve_button.pack(side="left")
    tk.Button(controls, text="Cancel", command=lambda: emit_control("cancel")).pack(side="left")
    mute_button = tk.Button(controls, text="Mute Voice", command=toggle_mute)
    mute_button.pack(side="left", padx=8)
    tk.Button(controls, text="Dismiss", command=dismiss).pack(side="right")

    def poll() -> None:
        nonlocal visible_preview_hash
        if not sys.stdin.closed:
            import select
            readable, _, _ = select.select([sys.stdin], [], [], 0)
            if readable:
                line = sys.stdin.readline()
                if line:
                    try:
                        event = json.loads(line)
                        transcript.set(event.get("transcript", ""))
                        status.set(event.get("status", event.get("state", "")))
                        response.set(event.get("response", ""))
                        context.set(f"Context: {event.get('context', 'unknown')}  Source: {event.get('source', '')}")
                        visible_preview_hash = event.get("preview_hash")
                        approve_button.configure(state="normal" if visible_preview_hash else "disabled")
                    except json.JSONDecodeError:
                        status.set("Invalid overlay event")
        root.after(100, poll)

    root.after(100, poll)
    root.mainloop()
    return 0
