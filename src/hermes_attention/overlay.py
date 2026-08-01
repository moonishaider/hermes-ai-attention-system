"""Lightweight local transcript/status overlay contract and optional Tk UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import sys
from typing import Callable


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

    for variable, size, color in (
        (transcript, 12, "#d1d5db"),
        (status, 10, "#93c5fd"),
        (response, 12, "#f9fafb"),
        (context, 9, "#a7f3d0"),
    ):
        tk.Label(root, textvariable=variable, font=("Helvetica", size), fg=color, bg="#111827", wraplength=520, justify="left").pack(anchor="w", padx=16, pady=4)

    controls = tk.Frame(root, bg="#111827")
    controls.pack(fill="x", padx=16, pady=8)
    tk.Button(controls, text="Cancel", command=lambda: print(json.dumps({"control": "cancel"}), flush=True)).pack(side="left")
    tk.Button(controls, text="Mute", command=lambda: print(json.dumps({"control": "mute"}), flush=True)).pack(side="left", padx=8)
    tk.Button(controls, text="Dismiss", command=root.withdraw).pack(side="right")

    def poll() -> None:
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
                    except json.JSONDecodeError:
                        status.set("Invalid overlay event")
        root.after(100, poll)

    root.after(100, poll)
    root.mainloop()
    return 0
