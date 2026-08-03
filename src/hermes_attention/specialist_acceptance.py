"""Deterministic specialist and scoped-memory acceptance checks."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

from .registry import SpecialistRegistry
from .storage import Store


def run_specialist_acceptance(specialist_root: Path) -> dict[str, Any]:
    registry = SpecialistRegistry(specialist_root)
    daily = registry.activate("daily-report", "inside-success")
    wrong_context_denied = False
    try:
        registry.activate("daily-report", "personal")
    except PermissionError:
        wrong_context_denied = True
    disabled_serious_denied = False
    try:
        registry.activate("tax-finance", "personal")
    except PermissionError:
        disabled_serious_denied = True
    tax = registry.specialists["tax-finance"]
    with tempfile.TemporaryDirectory(prefix="hermes-specialist-acceptance-") as temporary:
        store = Store(Path(temporary) / "state.sqlite3")
        try:
            store.propose_memory("inside-memory", "private placeholder", daily.memory_namespace, "inside-success", (), 0.8)
            store.propose_memory("personal-memory", "private placeholder", "personal", "personal", (), 0.8)
            rows = store.connection.execute(
                "SELECT namespace, context_id, COUNT(*) AS total FROM memory_proposals GROUP BY namespace, context_id"
            ).fetchall()
            pairs = {(row["namespace"], row["context_id"]): row["total"] for row in rows}
        finally:
            store.close()
    checks = {
        "daily_report_loaded": daily.specialist_id == "daily-report",
        "daily_report_context_locked": wrong_context_denied,
        "daily_report_publish_prohibited": "report.publish" in daily.prohibited_tools,
        "tax_finance_disabled": disabled_serious_denied and tax.status == "disabled",
        "tax_finance_serious_mode": tax.serious_mode and tax.model_route == "review",
        "tax_finance_payment_prohibited": "payment" in tax.prohibited_tools,
        "memory_contexts_isolated": pairs == {("personal", "personal"): 1, ("reports", "inside-success"): 1},
    }
    return {
        "schema_version": 1,
        "accepted": all(checks.values()),
        "checks": checks,
        "specialist_count": len(registry.specialists),
        "private_content_stored": False,
        "external_action_performed": False,
    }
