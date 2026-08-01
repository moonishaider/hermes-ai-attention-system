"""Conservative deterministic candidate extraction from untrusted evidence."""

from __future__ import annotations

from hashlib import sha256
import re

from .domain import TaskRecord


COMMITMENT_PATTERNS = [
    re.compile(r"\bI will\s+(.{5,180}?)(?:[.!?]|$)", re.I),
    re.compile(r"\bI(?:'ll|’ll)\s+(.{5,180}?)(?:[.!?]|$)", re.I),
    re.compile(r"\bplease\s+(.{5,180}?)(?:[.!?]|$)", re.I),
    re.compile(r"\bTODO\s*[:\-]\s*(.{5,180}?)(?:\n|$)", re.I),
]


def extract_task_candidates(content: str, evidence_id: str, context_id: str) -> list[TaskRecord]:
    candidates: list[TaskRecord] = []
    seen: set[str] = set()
    for pattern in COMMITMENT_PATTERNS:
        for match in pattern.finditer(content):
            title = " ".join(match.group(1).split()).strip()
            normalized = title.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            task_id = "candidate:" + sha256(f"{evidence_id}:{normalized}".encode()).hexdigest()[:24]
            candidates.append(
                TaskRecord(
                    task_id=task_id,
                    title=title,
                    context_id=context_id,
                    task_type="commitment-candidate",
                    status="triage",
                    priority=50,
                    evidence_ids=(evidence_id,),
                    confidence=0.6,
                )
            )
    return candidates


def find_contradictions(claims: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Flag explicit positive/negative duplicates for human review; never resolves them."""
    normalized: dict[str, tuple[str, str, bool]] = {}
    contradictions: list[dict[str, str]] = []
    for evidence_id, claim in claims:
        compact = " ".join(claim.casefold().split())
        negative = any(token in compact.split() for token in ("not", "never", "no"))
        key = " ".join(token for token in compact.split() if token not in {"not", "never", "no"})
        prior = normalized.get(key)
        if prior and prior[2] != negative:
            contradictions.append(
                {
                    "claim_a": prior[1],
                    "evidence_a": prior[0],
                    "claim_b": claim,
                    "evidence_b": evidence_id,
                    "status": "requires-user-resolution",
                }
            )
        normalized[key] = (evidence_id, claim, negative)
    return contradictions
