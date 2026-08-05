"""Facade exposed to Hermes tools and local CLI workflows."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .actions import ActionController
from .attention import AttentionEngine
from .config import ProjectPaths, load_json, validate_project_configuration
from .context_time import resolve_context_window
from .domain import ConfidenceState, EvidenceItem, Provenance, RiskClass, TaskRecord
from .extraction import extract_task_candidates
from .models import ModelRouter
from .policy import PolicyEngine
from .registry import IntegrationRegistry, SpecialistRegistry
from .routing import ContextRouter
from .security import detect_prompt_injection, redact_secrets
from .storage import Store


class AttentionService:
    def __init__(self, *, paths: ProjectPaths | None = None, database: Path | str | None = None) -> None:
        self.paths = paths or ProjectPaths.discover()
        configuration_errors = validate_project_configuration(self.paths)
        if configuration_errors:
            raise ValueError("invalid project configuration: " + "; ".join(configuration_errors))
        self.context_config = load_json(self.paths.config_dir / "contexts.json")
        self.model_config = load_json(self.paths.config_dir / "models.json")
        self.integration_config = load_json(self.paths.config_dir / "integrations.json")
        self.store = Store(database or self.paths.database)
        self.router = ContextRouter(self.context_config)
        self.policy = PolicyEngine(external_writes_enabled=False)
        self.actions = ActionController(self.store, self.policy)
        self.attention = AttentionEngine(self.store)
        self.models = ModelRouter(self.model_config, self.store)
        self.specialists = SpecialistRegistry(self.paths.specialist_dir)
        self.integrations = IntegrationRegistry(self.integration_config)

    def close(self) -> None:
        self.store.close()

    def status(self) -> dict[str, Any]:
        return {
            "service": "hermes-attention",
            "version": "0.1.0",
            "project_root": str(self.paths.root),
            "database": str(self.paths.database),
            "external_writes_enabled": self.policy.external_writes_enabled,
            "kill_switch": self.policy.kill_switch,
            "contexts": sorted(self.router.contexts),
            "specialists": sorted(self.specialists.specialists),
            "integrations": {key: value["mode"] for key, value in self.integrations.connections.items()},
            "budget": self.models.budget_status(),
        }

    def context_time_window(self, context_id: str, relative_date: str = "today") -> dict[str, Any]:
        return resolve_context_window(self.context_config, context_id, relative_date)

    def ingest_evidence(
        self,
        *,
        title: str,
        content: str,
        provenance: dict[str, Any],
        context_hints: tuple[str, ...] = (),
        extract_tasks: bool = True,
    ) -> dict[str, Any]:
        redacted, secret_count = redact_secrets(content)
        injection_flags = detect_prompt_injection(redacted)
        source = Provenance(**provenance)
        contexts = self.router.classify(source, hints=context_hints)
        evidence_id = f"{source.source_system}:{source.connection_id}:{source.source_id}"
        item = EvidenceItem(
            evidence_id=evidence_id,
            title=title,
            content=redacted,
            provenance=source,
            contexts=contexts,
            confidence_state=ConfidenceState.UNCERTAIN if injection_flags else ConfidenceState.INFERRED,
        )
        inserted = self.store.add_evidence(item)
        candidates = []
        primary_context = next((label.context_id for label in contexts if label.context_id != "mixed"), "unknown")
        if inserted and extract_tasks:
            candidates = extract_task_candidates(redacted, evidence_id, primary_context)
            for task in candidates:
                self.store.upsert_task(task)
        self.store.audit(
            "ingestion",
            "evidence.upsert",
            primary_context,
            "success",
            {
                "evidence_id": evidence_id,
                "inserted": inserted,
                "secret_redactions": secret_count,
                "prompt_injection_flags": len(injection_flags),
                "task_candidates": len(candidates),
            },
        )
        return {
            "evidence_id": evidence_id,
            "inserted": inserted,
            "contexts": [asdict(label) for label in contexts],
            "secret_redactions": secret_count,
            "prompt_injection_flags": injection_flags,
            "task_candidates": [asdict(task) for task in candidates],
        }

    def search(self, query: str, *, context_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        return self.store.search_evidence(query, context_id=context_id, limit=limit)

    def add_task(
        self,
        *,
        title: str,
        context_id: str,
        task_type: str = "task",
        priority: int = 50,
        evidence_ids: tuple[str, ...] = (),
    ) -> TaskRecord:
        if context_id not in self.router.contexts:
            raise ValueError(f"unknown context: {context_id}")
        task = TaskRecord(
            task_id=str(uuid4()),
            title=title,
            context_id=context_id,
            task_type=task_type,
            status="open",
            priority=max(0, min(priority, 100)),
            evidence_ids=evidence_ids,
            confidence=1.0,
        )
        self.store.upsert_task(task)
        return task

    def attention_queue(self, *, context_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        return self.attention.queue(context_id=context_id, limit=limit)

    def context_handoff(self, context_id: str) -> dict[str, Any]:
        if context_id not in self.router.contexts:
            raise ValueError(f"unknown context: {context_id}")
        return self.attention.context_handoff(context_id)

    def propose_action(
        self,
        *,
        action_type: str,
        context_id: str,
        risk_class: str,
        target: dict[str, Any],
        payload: dict[str, Any],
        evidence_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        risk = RiskClass(risk_class)
        profile = self.router.browser_profile(context_id)
        proposal = self.actions.propose(
            action_type=action_type,
            context_id=context_id,
            risk_class=risk,
            target=target,
            payload=payload,
            evidence_ids=evidence_ids,
            browser_profile=profile,
        )
        decision = self.policy.validate_proposal(proposal)
        return {"proposal": asdict(proposal), "policy": asdict(decision), "execution_performed": False}

    def request_screen_view(self, *, reason: str, context_id: str) -> dict[str, Any]:
        return {
            "request_id": str(uuid4()),
            "reason": reason,
            "context": context_id,
            "state": "awaiting-explicit-local-capture",
            "capture_performed": False,
            "retention": "temporary-unless-promoted",
            "message": "Screen capture remains a user-triggered local capability and is not executed by this tool.",
        }

    def daily_report_draft(self, report_date: str) -> dict[str, Any]:
        tasks = self.store.list_tasks(context_id="inside-success", statuses=("open", "blocked", "done"))
        lines = []
        sources: list[str] = []
        for task in tasks:
            evidence_ids = task["evidence_ids_json"]
            if evidence_ids == "[]":
                continue
            lines.append(f"- [{task['status']}] {task['title']}")
            sources.append(evidence_ids)
        return {
            "date": report_date,
            "context": "inside-success",
            "text": "\n".join(lines) if lines else "No sufficiently evidenced activity is available.",
            "evidence_references": sources,
            "state": "draft",
            "requires_exact_preview_and_approval": True,
            "publisher_enabled": False,
        }
