"""Project-local command line for diagnostics and explicit ingestion workflows."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .config import ProjectPaths, validate_project_configuration
from .history import ChatGPTExportImporter, CodexHistoryBridge, ContextRelayImporter
from .overlay import run_tk_overlay
from .service import AttentionService


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-attention")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="validate local non-secret configuration")
    commands.add_parser("status", help="show safe runtime status")

    search = commands.add_parser("search", help="search local evidence")
    search.add_argument("query")
    search.add_argument("--context")
    search.add_argument("--limit", type=int, default=10)

    queue = commands.add_parser("attention", help="show ranked attention queue")
    queue.add_argument("--context")
    queue.add_argument("--limit", type=int, default=10)

    codex = commands.add_parser("codex-history", help="preview or ingest Codex history read-only")
    codex.add_argument("action", choices=("preview", "ingest"))
    codex.add_argument("--maximum-records", type=int, default=500)

    chatgpt = commands.add_parser("chatgpt-export", help="preview or import an official ChatGPT export")
    chatgpt.add_argument("action", choices=("preview", "import"))
    chatgpt.add_argument("path", type=Path)
    chatgpt.add_argument("--start-date", default="2026-04-01")
    chatgpt.add_argument("--confirmed", action="store_true")

    relay = commands.add_parser("context-relay", help="ingest one explicit ChatGPT context relay")
    relay.add_argument("path", type=Path)

    handoff = commands.add_parser("handoff", help="build a concise context-switch handoff")
    handoff.add_argument("context")

    report = commands.add_parser("daily-report", help="draft an evidence-only Inside Success report")
    report.add_argument("date")

    commands.add_parser("overlay", help="run the optional local Tk overlay; reads JSON events from stdin")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "doctor":
        paths = ProjectPaths.discover()
        errors = validate_project_configuration(paths)
        emit({"ok": not errors, "project_root": str(paths.root), "errors": errors, "secrets_printed": False})
        return 1 if errors else 0
    if arguments.command == "overlay":
        return run_tk_overlay()

    service = AttentionService()
    try:
        if arguments.command == "status":
            emit(service.status())
        elif arguments.command == "search":
            emit(service.search(arguments.query, context_id=arguments.context, limit=arguments.limit))
        elif arguments.command == "attention":
            emit(service.attention_queue(context_id=arguments.context, limit=arguments.limit))
        elif arguments.command == "codex-history":
            bridge = CodexHistoryBridge(service.store, service.router)
            emit(bridge.preview() if arguments.action == "preview" else bridge.ingest(maximum_records=arguments.maximum_records))
        elif arguments.command == "chatgpt-export":
            importer = ChatGPTExportImporter(service.store, service.router)
            if arguments.action == "preview":
                emit(importer.preview(arguments.path, start_date=arguments.start_date))
            else:
                emit(importer.ingest(arguments.path, start_date=arguments.start_date, confirmed=arguments.confirmed))
        elif arguments.command == "context-relay":
            emit({"inserted": ContextRelayImporter(service.store, service.router).ingest(arguments.path)})
        elif arguments.command == "handoff":
            emit(service.context_handoff(arguments.context))
        elif arguments.command == "daily-report":
            emit(service.daily_report_draft(arguments.date))
        return 0
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
