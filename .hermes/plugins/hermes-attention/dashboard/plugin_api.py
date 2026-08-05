"""Narrow native-Desktop API for the Hermes Attention project plugin.

The router exposes local status, queues, local task creation, and the existing
explicit one-shot screen adapter. It has no external connector writer, action
approval endpoint, executor, arbitrary path parameter, or browser control.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src"
if str(SRC) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SRC))

from hermes_attention.screen import understand_screen_once  # noqa: E402
from hermes_attention.config import ProjectPaths  # noqa: E402
from hermes_attention.service import AttentionService  # noqa: E402


router = APIRouter()
ContextId = Literal["inside-success", "mitchell", "personal", "mixed", "unknown"]
PROJECT_PATHS = ProjectPaths.discover(ROOT)


def _service() -> AttentionService:
    """Open the marked project regardless of the Desktop process cwd."""
    return AttentionService(paths=PROJECT_PATHS)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    context_id: ContextId
    priority: int = Field(default=50, ge=0, le=100)


class ScreenRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    context_id: Literal["inside-success", "mitchell", "personal"]


def _latest_action(service: AttentionService) -> dict | None:
    row = service.store.connection.execute(
        "SELECT proposal_json, preview_hash, state, updated_at "
        "FROM actions ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    proposal = json.loads(row["proposal_json"])
    return {
        "proposal_id": proposal.get("proposal_id"),
        "action_type": proposal.get("action_type"),
        "context_id": proposal.get("context_id"),
        "risk_class": proposal.get("risk_class"),
        "target": proposal.get("target"),
        "preview_hash": row["preview_hash"],
        "state": row["state"],
        "expires_at": proposal.get("expires_at"),
        "updated_at": row["updated_at"],
        "execution_available": False,
    }


@router.get("/home")
async def home(context_id: ContextId = "unknown") -> dict:
    service = _service()
    try:
        status = service.status()
        queue = service.attention_queue(context_id=context_id, limit=12)
        return {
            "status": status,
            "context_id": context_id,
            "queue": queue,
            "latest_action": _latest_action(service),
            "learning": {
                "memory_writes": "review-required",
                "skill_writes": "review-required",
                "journey": "native-memory-graph",
                "curator": "archive-only-no-bundled-pruning",
            },
        }
    finally:
        service.close()


@router.post("/tasks")
async def create_task(body: TaskCreate) -> dict:
    service = _service()
    try:
        task = service.add_task(
            title=body.title.strip(),
            context_id=body.context_id,
            priority=body.priority,
        )
        service.store.audit(
            "hermes-desktop",
            "task.create.local",
            body.context_id,
            "success",
            {"task_id": task.task_id, "external_write": False},
        )
        return {"task": asdict(task), "external_write": False}
    finally:
        service.close()


@router.post("/screen")
async def view_screen_once(body: ScreenRequest) -> dict:
    try:
        return await run_in_threadpool(
            understand_screen_once,
            body.reason.strip(),
            body.context_id,
            PROJECT_PATHS,
        )
    except (RuntimeError, ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
