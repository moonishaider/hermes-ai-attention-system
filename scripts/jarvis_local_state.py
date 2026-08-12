#!/usr/bin/env python3
"""Narrow JSON bridge for Jarvis-owned state and explicit read-only adapters."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.capabilities import CapabilityStudio
from hermes_attention.computer_awareness import AwarenessPolicy
from hermes_attention.domain import utc_now
from hermes_attention.google_direct import PersonalGoogleDirect
from hermes_attention.service import AttentionService


CONTEXTS = {"inside-success", "mitchell", "personal", "mixed", "unknown"}
KINDS = {"mission", "radar", "capability"}
APPROVED_CAPABILITY_TOOLS = {"search_evidence", "public_web_search", "ledger_query", "daily_brief"}
RADAR_SOURCES = {"public-web", "github", "slack", "calendar", "zoom", "codex"}


def bounded(value: Any, *, maximum: int, name: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > maximum:
        raise ValueError(f"{name} must contain 1 to {maximum} characters")
    return text


def state(service: AttentionService, context_id: str) -> dict[str, Any]:
    connection = service.store.connection
    projects = [dict(row) for row in connection.execute(
        "SELECT project_id,name,objective,phase,lifecycle,freshness_at FROM projects "
        "WHERE context_id=? ORDER BY updated_at DESC LIMIT 20", (context_id,),
    )]
    missions = [dict(row) for row in connection.execute(
        "SELECT mission_id,goal,completion_contract,state AS status,lifecycle,review_cadence FROM missions "
        "WHERE context_id=? ORDER BY updated_at DESC LIMIT 20", (context_id,),
    )]
    radars = [dict(row) for row in connection.execute(
        "SELECT radar_id,question,cadence,notification_policy,lifecycle FROM radars "
        "WHERE context_id=? ORDER BY updated_at DESC LIMIT 20", (context_id,),
    )]
    capabilities = [dict(row) for row in connection.execute(
        "SELECT capability_id,kind,status,spec_json,updated_at FROM capabilities "
        "WHERE context_id=? ORDER BY updated_at DESC LIMIT 20", (context_id,),
    )]
    for item in capabilities:
        spec = json.loads(item.pop("spec_json"))
        item["name"] = str(spec.get("name") or spec.get("description") or item["kind"])
    ledger_count = connection.execute(
        "SELECT count(*) FROM ledger_entries WHERE context_id=?", (context_id,)
    ).fetchone()[0]
    task_count = connection.execute(
        "SELECT count(*) FROM tasks WHERE context_id=? AND status='open'", (context_id,)
    ).fetchone()[0]
    status_value = service.status()
    timezone = {
        "inside-success": "America/New_York", "mitchell": "America/New_York",
        "personal": "Asia/Karachi",
    }.get(context_id)
    local_date = datetime.now(ZoneInfo(timezone)).date().isoformat() if timezone else None
    proactive = service.proactive.start_of_day(context_id=context_id, local_date=local_date) if local_date else None
    focus_sessions = [dict(row) for row in connection.execute(
        """SELECT focus_id,context_id,mode,started_at,expires_at,stopped_at
           FROM focus_sessions WHERE context_id=? ORDER BY started_at DESC LIMIT 5""", (context_id,),
    )]
    for item in focus_sessions:
        observations = [dict(row) for row in connection.execute(
            """SELECT occurred_at,app_id,domain,browser_profile,context_id
               FROM observation_events WHERE focus_id=? ORDER BY occurred_at DESC LIMIT 12""",
            (item["focus_id"],),
        )]
        item["observations"] = observations
    proposals = [dict(row) for row in connection.execute(
        """SELECT proposal_id,signature,status,occurrence_count,estimated_time_saved_minutes,false_alerts
           FROM automation_proposals WHERE context_id=? ORDER BY updated_at DESC LIMIT 10""", (context_id,),
    )]
    style = connection.execute(
        """SELECT profile_id,review_status,profile_json,evidence_window_json,updated_at
           FROM calendar_style_profiles WHERE account_id='personal' ORDER BY updated_at DESC LIMIT 1"""
    ).fetchone() if context_id == "personal" else None
    style_value = None
    if style:
        style_value = dict(style)
        # Calendar style contains aggregate habits only. Event titles, attendee
        # identities, descriptions, and raw event bodies are never persisted.
        style_value["profile"] = json.loads(style_value.pop("profile_json"))
        style_value["evidence_window"] = json.loads(style_value.pop("evidence_window_json"))
    background_row = connection.execute(
        "SELECT value_json FROM runtime_settings WHERE key='background_intelligence'"
    ).fetchone()
    recent_ledger = [dict(row) for row in connection.execute(
        """SELECT entry_id,kind,occurred_at_utc,local_date,actor_state,summary,
                  confidence_state,freshness_at,project_id,task_id
           FROM ledger_entries WHERE context_id=?
           ORDER BY occurred_at_utc DESC LIMIT 25""", (context_id,),
    )]
    for item in recent_ledger:
        item["evidence_ids"] = [row["evidence_id"] for row in connection.execute(
            "SELECT evidence_id FROM ledger_sources WHERE entry_id=? ORDER BY evidence_id",
            (item["entry_id"],),
        )]
    commitments = [dict(row) for row in connection.execute(
        """SELECT task_id,title,status,due_at,evidence_ids_json,confidence,updated_at
           FROM tasks WHERE context_id=? AND task_type='commitment'
           ORDER BY updated_at DESC LIMIT 12""", (context_id,),
    )]
    for item in commitments:
        item["evidence_ids"] = json.loads(item.pop("evidence_ids_json"))
    recent_decisions = [dict(row) for row in connection.execute(
        """SELECT decision_id,decision,reasoning,decided_at,review_at,actual_outcome
           FROM decisions WHERE context_id=? ORDER BY decided_at DESC LIMIT 12""", (context_id,),
    )]
    action_previews = [dict(row) for row in connection.execute(
        """SELECT proposal_id,preview_hash,state,updated_at
           FROM actions ORDER BY updated_at DESC LIMIT 10""",
    )]
    learning = [dict(row) for row in connection.execute(
        """SELECT memory_id,statement,namespace,confidence,status,created_at
           FROM memory_proposals WHERE context_id=? ORDER BY created_at DESC LIMIT 10""", (context_id,),
    )]
    return {
        "ok": True,
        "context": context_id,
        "ledgerCount": ledger_count,
        "openTaskCount": task_count,
        "projects": projects,
        "missions": missions,
        "radars": radars,
        "capabilities": capabilities,
        "budget": status_value["budget"],
        "integrations": status_value["integrations"],
        "codexSync": status_value["codex_sync"],
        "killSwitch": status_value["kill_switch"],
        "proactive": proactive,
        "focusSessions": focus_sessions,
        "automationProposals": proposals,
        "calendarStyle": style_value,
        "backgroundMode": json.loads(background_row["value_json"]) if background_row else "running",
        "recentLedger": recent_ledger,
        "commitments": commitments,
        "recentDecisions": recent_decisions,
        "actionPreviews": action_previews,
        "learningItems": learning,
    }


def create(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    kind = str(value.get("kind") or "")
    context_id = str(value.get("context") or "")
    if kind not in KINDS or context_id not in CONTEXTS:
        raise ValueError("unsupported local item kind or context")
    if kind == "mission":
        identifier = service.missions.create(
            context_id=context_id,
            goal=bounded(value.get("title"), maximum=500, name="goal"),
            completion_contract=bounded(value.get("details"), maximum=1_000, name="completion contract"),
            review_cadence="weekly",
        )
        return {"ok": True, "kind": kind, "id": identifier, "status": "active"}
    if kind == "radar":
        requested_sources = {str(item) for item in value.get("sources", ["public-web"])}
        if not requested_sources or not requested_sources <= RADAR_SOURCES:
            raise ValueError("radar sources exceed the approved read-only inventory")
        identifier = service.radars.create(
            context_id=context_id,
            question=bounded(value.get("title"), maximum=500, name="radar question"),
            sources=sorted(requested_sources), cadence="weekly",
            material_change={"meaningful_change": True}, notification_policy="digest",
        )
        return {"ok": True, "kind": kind, "id": identifier, "status": "active"}
    studio = CapabilityStudio(service.store, APPROVED_CAPABILITY_TOOLS)
    spec = {
        "kind": "workflow", "context_id": context_id,
        "name": bounded(value.get("title"), maximum=200, name="capability name"),
        "description": bounded(value.get("details"), maximum=1_000, name="description"),
        "tools": sorted({str(item) for item in value.get("tools", ["search_evidence"])}),
        "requires_code": bool(value.get("requiresCode", False)),
    }
    result = studio.create(
        spec, permission_inventory={tool: "read/local" for tool in APPROVED_CAPABILITY_TOOLS},
    )
    if result.get("status") == "codex-spec-only":
        return {"ok": True, "kind": kind, "status": "codex-spec-only", "activationPerformed": False}
    dry = studio.dry_run(
        result["capability_id"],
        current_permission_inventory={tool: "read/local" for tool in APPROVED_CAPABILITY_TOOLS},
    )
    return {
        "ok": True, "kind": kind, "id": result["capability_id"],
        "status": "draft", "dryRun": dry, "activationPerformed": False,
    }


def focus(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    context_id = str(value.get("context") or "")
    minutes = int(value.get("minutes") or 0)
    if context_id not in CONTEXTS or context_id in {"mixed", "unknown"}:
        raise ValueError("focus requires one explicit active context")
    focus_id = service.computer_awareness.start_focus(
        context_id=context_id, minutes=minutes, policy=AwarenessPolicy(),
    )
    return {"ok": True, "focusId": focus_id, "minutes": minutes, "visibleIndicator": True}


def stop_focus(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    focus_id = bounded(value.get("focusId"), maximum=100, name="focus id")
    service.computer_awareness.stop(focus_id)
    return {"ok": True, "focusId": focus_id, "stopped": True}


def observe(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    focus_id = bounded(value.get("focusId"), maximum=100, name="focus id")
    context_id = str(value.get("context") or "")
    if context_id not in CONTEXTS or context_id in {"mixed", "unknown"}:
        raise ValueError("observation requires one explicit context")
    app_id = bounded(value.get("appId"), maximum=300, name="application identity")
    # The app name is display-only metadata and never substitutes for a proven
    # browser profile/domain identity.
    app_name = bounded(value.get("appName"), maximum=300, name="application name")
    event_id = service.computer_awareness.observe_metadata(
        focus_id=focus_id, app_id=app_id, window_title=app_name,
        domain=None, browser_profile=None, context_id=context_id,
    )
    return {
        "ok": True, "eventId": event_id, "appId": app_id,
        "profile": None, "screenshotsRetained": 0,
    }


def setting(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    mode = str(value.get("mode") or "")
    if mode not in {"off", "running", "login"}:
        raise ValueError("invalid background intelligence mode")
    with service.store.connection:
        service.store.connection.execute(
            """INSERT INTO runtime_settings VALUES('background_intelligence',?,?)
               ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at""",
            (json.dumps(mode), utc_now()),
        )
    return {"ok": True, "mode": mode}


def calendar_profile(service: AttentionService, _value: dict[str, Any]) -> dict[str, Any]:
    end = datetime.now(UTC)
    start = end - timedelta(days=365)
    sample = PersonalGoogleDirect().calendar_style_events(
        start.isoformat(), end.isoformat(), maximum=500,
    )
    result = service.calendar_style.derive(
        account_id="personal", calendar_id=str(sample["calendar_id"]),
        events=list(sample["events"]), window_start=start.isoformat(), window_end=end.isoformat(),
    )
    return {
        "ok": True,
        "profileId": result["profile_id"],
        "reviewStatus": result["review_status"],
        "sampleSize": result["profile"]["sample_size"],
    }


def review_calendar_profile(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    profile_id = bounded(value.get("profileId"), maximum=100, name="profile id")
    # This local acknowledgement only confirms the displayed derived profile;
    # specific corrections remain owner-supplied structured fields.
    return service.calendar_style.review(profile_id, corrections={})


def projection(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    context_id = str(value.get("context") or "")
    mode = str(value.get("mode") or "")
    if context_id not in {"inside-success", "mitchell", "personal"}:
        raise ValueError("projection requires one explicit context")
    timezone = {"inside-success": "America/New_York", "mitchell": "America/New_York", "personal": "Asia/Karachi"}[context_id]
    local_today = datetime.now(ZoneInfo(timezone)).date()
    if mode == "start-of-day":
        output = service.proactive.start_of_day(context_id=context_id, local_date=local_today.isoformat())
    elif mode == "end-of-day":
        output = service.proactive.end_of_day(context_id=context_id, local_date=local_today.isoformat())
    elif mode == "pre-meeting":
        output = service.proactive.pre_meeting(context_id=context_id)
    elif mode == "absence-return":
        dates = [(local_today - timedelta(days=offset)).isoformat() for offset in range(1, 4)]
        output = service.proactive.absence_return(context_id=context_id, dates=dates)
    else:
        raise ValueError("unsupported proactive projection")
    return {"ok": True, "externalWrite": False, "projection": output}


def capability_control(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    capability_id = bounded(value.get("capabilityId"), maximum=100, name="capability id")
    action = str(value.get("action") or "")
    studio = CapabilityStudio(service.store, APPROVED_CAPABILITY_TOOLS)
    if action in {"disabled", "archived"}:
        studio.set_status(capability_id, action)
        return {"ok": True, "capabilityId": capability_id, "status": action}
    if action in {"useful", "not-useful"}:
        feedback_id = studio.record_feedback(
            capability_id=capability_id, useful=action == "useful",
            correction=None, evidence_ids=(),
            provenance={"source": "jarvis-owner-local-ui", "reversible": True},
        )
        return {"ok": True, "capabilityId": capability_id, "feedbackId": feedback_id}
    raise ValueError("unsupported capability action")


def automation_outcome(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    proposal_id = bounded(value.get("proposalId"), maximum=100, name="proposal id")
    outcome = str(value.get("outcome") or "")
    service.automation_miner.record_outcome(proposal_id, outcome)
    return {"ok": True, "proposalId": proposal_id, "outcome": outcome}


def record_model_decision(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    run_id = bounded(value.get("runId"), maximum=80, name="run id")
    if not run_id.startswith("run_"):
        raise ValueError("model decision requires a Hermes run id")
    route = str(value.get("route") or "")
    if route not in {"routine", "difficult", "review"}:
        raise ValueError("invalid model decision route")
    outcome = str(value.get("outcome") or "")
    if outcome not in {"success", "failed", "cancelled"}:
        raise ValueError("invalid model decision outcome")
    context_id = str(value.get("context") or "")
    if context_id not in CONTEXTS:
        raise ValueError("invalid model decision context")
    latency_ms = max(0, min(int(value.get("latencyMs") or 0), 3_600_000))
    cost_usd = max(0.0, min(float(value.get("costUsd") or 0), 100.0))
    signals = {
        "source": "jarvis-front-controller",
        "context": context_id,
        "provider": bounded(value.get("provider"), maximum=80, name="provider"),
        "model": bounded(value.get("model"), maximum=120, name="model"),
    }
    with service.store.connection:
        service.store.connection.execute(
            """INSERT INTO model_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(run_id) DO UPDATE SET latency_ms=excluded.latency_ms,
                 cost_usd=excluded.cost_usd,outcome=excluded.outcome""",
            (
                run_id, route, bounded(value.get("reason"), maximum=300, name="reason"),
                json.dumps(signals, sort_keys=True), None, None,
                "review" if value.get("reviewerRoute") == "review" else None,
                latency_ms, cost_usd, outcome, utc_now(),
            ),
        )
    return {"ok": True, "runId": run_id, "recorded": True}


def commitment_open(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    context_id = str(value.get("context") or "")
    if context_id not in {"inside-success", "mitchell", "personal"}:
        raise ValueError("commitment requires one explicit context")
    evidence_id = bounded(value.get("evidenceId"), maximum=160, name="source evidence")
    linked = service.store.connection.execute(
        """SELECT 1 FROM ledger_sources ls JOIN ledger_entries le ON le.entry_id=ls.entry_id
           WHERE ls.evidence_id=? AND le.context_id=? LIMIT 1""",
        (evidence_id, context_id),
    ).fetchone()
    if not linked:
        raise ValueError("commitment source is not ledger evidence in this context")
    task_id = service.ledger.open_commitment(
        title=bounded(value.get("title"), maximum=500, name="commitment title"),
        context_id=context_id, evidence_ids=(evidence_id,),
    )
    return {"ok": True, "taskId": task_id, "status": "open", "externalWrite": False}


def commitment_complete(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    task_id = bounded(value.get("taskId"), maximum=100, name="commitment id")
    evidence_id = bounded(value.get("evidenceId"), maximum=160, name="completion evidence")
    task = service.store.connection.execute(
        "SELECT context_id FROM tasks WHERE task_id=? AND task_type='commitment' AND status='open'",
        (task_id,),
    ).fetchone()
    if not task:
        raise ValueError("open commitment not found")
    linked = service.store.connection.execute(
        """SELECT 1 FROM ledger_sources ls JOIN ledger_entries le ON le.entry_id=ls.entry_id
           WHERE ls.evidence_id=? AND le.context_id=? LIMIT 1""",
        (evidence_id, task["context_id"]),
    ).fetchone()
    if not linked:
        raise ValueError("completion proof is not ledger evidence in the commitment context")
    service.ledger.verify_commitment_complete(task_id, evidence_id=evidence_id)
    return {"ok": True, "taskId": task_id, "status": "completed", "externalWrite": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "operation",
        choices=("state", "create", "focus", "stop-focus", "observe", "setting", "calendar-profile", "review-calendar-profile", "projection", "capability-control", "automation-outcome", "record-model-decision", "commitment-open", "commitment-complete"),
    )
    parser.add_argument("--context")
    arguments = parser.parse_args()
    try:
        service = AttentionService()
        try:
            if arguments.operation == "state":
                if arguments.context not in CONTEXTS:
                    raise ValueError("invalid context")
                output = state(service, arguments.context)
            else:
                raw = sys.stdin.buffer.read(32_769)
                if len(raw) > 32_768:
                    raise ValueError("local item request is too large")
                value = json.loads(raw or b"{}")
                output = {
                    "create": create, "focus": focus, "stop-focus": stop_focus, "observe": observe, "setting": setting,
                    "calendar-profile": calendar_profile,
                    "review-calendar-profile": review_calendar_profile,
                    "projection": projection,
                    "capability-control": capability_control,
                    "automation-outcome": automation_outcome,
                    "record-model-decision": record_model_decision,
                    "commitment-open": commitment_open,
                    "commitment-complete": commitment_complete,
                }[arguments.operation](service, value)
        finally:
            service.close()
        print(json.dumps(output, sort_keys=True))
        return 0
    except (ValueError, TypeError, RuntimeError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
