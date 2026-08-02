"""Cost-bounded representative model quality evaluation with private outputs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
from typing import Any

from .runtime_models import DirectModelClient


@dataclass(frozen=True, slots=True)
class QualityTask:
    task_id: str
    prompt: str
    required_markers: tuple[str, ...]
    forbidden_markers: tuple[str, ...] = ()


ROUTINE_TASKS = (
    QualityTask(
        "routine_grounding",
        "Evidence: [S1][inside-success][inferred] Codex says: I will finish the acceptance report. [S2][personal][confirmed] GitHub records the rollback checkpoint. Produce a two-item brief. Preserve contexts, cite every item, and label confidence.",
        ("[s1]", "[s2]", "inside-success", "personal"),
    ),
    QualityTask(
        "routine_attribution",
        "Evidence: [S1][inside-success] Alex completed the migration. [S2][inside-success] Syed reviewed the logs. State only what Syed did, cite it, and do not attribute Alex's work to Syed.",
        ("[s2]", "reviewed"), ("syed completed the migration",),
    ),
)

DIFFICULT_TASK = QualityTask(
    "difficult_contradiction",
    "[S1][confirmed] The release is ready. [S2][confirmed] The release is not ready. Explain the decision state without resolving the contradiction. Cite both sources and state what human judgment is required.",
    ("[s1]", "[s2]", "contrad"), ("there is no contradiction",),
)

REVIEW_TASK = QualityTask(
    "review_misattribution",
    "High-stakes review. Evidence says [S1] Alex completed deployment and [S2] Syed reviewed logs. Draft says: Syed completed deployment. Identify the attribution defect, cite evidence, and state whether this draft should be published.",
    ("[s1]", "[s2]", "attribut", "not"), ("safe to publish",),
)


def deterministic_quality(text: str, task: QualityTask) -> dict[str, Any]:
    normalized = " ".join(text.casefold().split())
    required_hits = sum(marker.casefold() in normalized for marker in task.required_markers)
    forbidden_hits = sum(marker.casefold() in normalized for marker in task.forbidden_markers)
    required_score = required_hits / len(task.required_markers) if task.required_markers else 1.0
    score = max(0.0, required_score - (forbidden_hits * 0.5))
    return {
        "score": round(score, 4), "required_hits": required_hits,
        "required_total": len(task.required_markers), "forbidden_hits": forbidden_hits,
    }


class ModelQualityEvaluator:
    def __init__(self, client: DirectModelClient, private_dir: Path) -> None:
        self.client = client
        self.private_dir = private_dir.resolve()
        self.private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.private_dir, 0o700)

    def _run(self, route: str, task: QualityTask, *, image_data_url: str | None = None) -> dict[str, Any]:
        result = self.client.generate(
            route, task.prompt, image_data_url=image_data_url,
            feature=f"quality-eval:{task.task_id}", max_output_tokens=512,
        )
        text = str(result.pop("text", ""))
        output_path = self.private_dir / f"{route}-{task.task_id}.txt"
        output_path.write_text(text, encoding="utf-8")
        os.chmod(output_path, 0o600)
        quality = deterministic_quality(text, task)
        return {
            "route": route, "task_id": task.task_id, "success": bool(result["success"]),
            "output_sha256": sha256(text.encode()).hexdigest(), "output_bytes": len(text.encode()),
            **quality,
            **{key: result[key] for key in ("provider", "model", "latency_ms", "input_tokens", "output_tokens", "estimated_cost_usd", "error_class")},
        }

    def run(self, *, routine_images: dict[str, str]) -> dict[str, Any]:
        rows = []
        for task in ROUTINE_TASKS:
            rows.append(self._run("routine", task))
            rows.append(self._run("vision", task, image_data_url=routine_images[task.task_id]))
        rows.append(self._run("difficult", DIFFICULT_TASK))
        rows.append(self._run("review", REVIEW_TASK))
        comparison = {}
        for route in ("routine", "vision"):
            items = [row for row in rows if row["route"] == route]
            comparison[route] = {
                "quality_mean": round(sum(row["score"] for row in items) / len(items), 4),
                "median_latency_ms": median(row["latency_ms"] for row in items),
                "cost_usd": round(sum(row["estimated_cost_usd"] for row in items), 8),
                "successes": sum(row["success"] for row in items),
            }
        return {
            "schema_version": 1, "rows": rows, "routine_comparison": comparison,
            "total_cost_usd": round(sum(row["estimated_cost_usd"] for row in rows), 8),
            "private_content_committed": False,
        }
