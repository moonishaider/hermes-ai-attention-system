#!/usr/bin/env python3
"""Narrow JSON bridge for Jarvis-owned state and explicit read-only adapters."""

from __future__ import annotations

import argparse
import base64
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
import json
import os
from pathlib import Path
import re
import secrets
import sys
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.capabilities import CapabilityStudio
from hermes_attention.computer_awareness import AwarenessPolicy
from hermes_attention.action_firewall import ActionFirewall
from hermes_attention.actions import ActionController
from hermes_attention.domain import ActionProposal, ActionState, RiskClass, stable_hash, utc_now
from hermes_attention.google_direct import PersonalGoogleDirect
from hermes_attention.personal_google_action_oauth import PersonalGoogleActionTokenManager
from hermes_attention.personal_google_actions import (
    PersonalCalendarActions, PersonalGmailDraftActions, PersonalGoogleActionTransport,
)
from hermes_attention.policy import PolicyEngine
from hermes_attention.service import AttentionService
from hermes_attention.web_research import search_public_web


CONTEXTS = {"inside-success", "mitchell", "personal", "mixed", "unknown"}
KINDS = {"mission", "radar", "capability"}
APPROVED_CAPABILITY_TOOLS = {"search_evidence", "public_web_search", "ledger_query", "daily_brief"}
RADAR_SOURCES = {"public-web", "github", "slack", "calendar", "zoom", "codex"}
PERSONAL_ACCOUNT = "moonishaider12@gmail.com"
CALENDAR_CAPABILITY = "personal-calendar-owned"
GMAIL_CAPABILITY = "personal-gmail-draft-only"
PERSONAL_ACTIONS_SETTING = "personal_google_actions_enabled"
PERSONAL_ACTIONS_MODE_SETTING = "personal_google_actions_mode"
PERSONAL_ACTION_MODES = {"off", "preview", "auto-explicit", "earned-auto"}


def bounded(value: Any, *, maximum: int, name: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > maximum:
        raise ValueError(f"{name} must contain 1 to {maximum} characters")
    return text


def _firewall_secret() -> bytes:
    path = ROOT / "runtime-data" / "action_firewall.key"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.exists():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(secrets.token_bytes(32)); handle.flush(); os.fsync(handle.fileno())
    if path.stat().st_mode & 0o077 or path.stat().st_size != 32:
        raise RuntimeError("personal action signing key is not owner-only or valid")
    return path.read_bytes()


def _personal_actions_enabled(service: AttentionService) -> bool:
    row = service.store.connection.execute(
        "SELECT value_json FROM runtime_settings WHERE key=?", (PERSONAL_ACTIONS_SETTING,),
    ).fetchone()
    return bool(row and json.loads(row["value_json"]) is True)


def _set_personal_actions_enabled(service: AttentionService, enabled: bool) -> None:
    with service.store.connection:
        service.store.connection.execute(
            """INSERT INTO runtime_settings VALUES(?,?,?)
               ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at""",
            (PERSONAL_ACTIONS_SETTING, json.dumps(enabled), utc_now()),
        )


def _personal_action_mode(service: AttentionService) -> str:
    row = service.store.connection.execute(
        "SELECT value_json FROM runtime_settings WHERE key=?", (PERSONAL_ACTIONS_MODE_SETTING,),
    ).fetchone()
    if row:
        value = str(json.loads(row["value_json"]))
        if value in PERSONAL_ACTION_MODES:
            return value
    return "auto-explicit" if _personal_actions_enabled(service) else "off"


def _set_personal_action_mode(service: AttentionService, mode: str) -> None:
    if mode not in PERSONAL_ACTION_MODES:
        raise ValueError("invalid personal action mode")
    with service.store.connection:
        service.store.connection.execute(
            """INSERT INTO runtime_settings VALUES(?,?,?)
               ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at""",
            (PERSONAL_ACTIONS_MODE_SETTING, json.dumps(mode), utc_now()),
        )


def _register_personal_capabilities(
    service: AttentionService, *, enable: bool, mode: str | None = None
) -> ActionFirewall:
    firewall = ActionFirewall(service.store, _firewall_secret(), global_kill_switch=False)
    effective_mode = mode or _personal_action_mode(service)
    autonomy_stage = {
        "off": 0,
        "preview": 3,
        "auto-explicit": 4,
        "earned-auto": 5,
    }[effective_mode]
    specs = ((CALENDAR_CAPABILITY, {"account": PERSONAL_ACCOUNT, "calendar_id": "primary"}, True),
             (GMAIL_CAPABILITY, {"account": PERSONAL_ACCOUNT, "resource": "draft"}, False))
    for capability, target, reversible in specs:
        inventory = {"account": PERSONAL_ACCOUNT, "capability": capability,
                     "methods": ["POST", "PATCH", "DELETE"] if reversible else ["POST", "PUT", "GET"]}
        firewall.register_capability(capability_id=capability, context_id="personal",
            account_id=PERSONAL_ACCOUNT, target_lock=target, permission_inventory=inventory,
            browser_profile="Profile 1", autonomy_stage=autonomy_stage,
            reversible=reversible, enabled=enable)
        firewall.set_capability_kill_switch(capability, not enable)
    return firewall


def personal_action_status(service: AttentionService, _value: dict[str, Any]) -> dict[str, Any]:
    status_value = PersonalGoogleActionTokenManager().status()
    enabled = bool(status_value["connected"] and _personal_actions_enabled(service))
    mode = _personal_action_mode(service)
    _register_personal_capabilities(service, enable=enabled, mode=mode)
    resources = [dict(row) for row in service.store.connection.execute(
        "SELECT resource_id,capability_id,provider_id,state,metadata_json,created_at,updated_at FROM external_resources "
        "WHERE capability_id IN (?,?) ORDER BY updated_at DESC LIMIT 10",
        (CALENDAR_CAPABILITY, GMAIL_CAPABILITY),
    )]
    for resource in resources:
        resource["metadata"] = json.loads(resource.pop("metadata_json") or "{}")
    return {"ok": True, **status_value, "resources": resources, "genericKillSwitch": True,
            "personalCapabilitiesEnabled": enabled, "mode": mode}


def personal_action_setting(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    enabled = value.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("personal action capability state must be true or false")
    connected = bool(PersonalGoogleActionTokenManager().status()["connected"])
    if enabled and not connected:
        raise PermissionError("personal Google actions must be connected before enabling capability execution")
    mode = str(value.get("mode") or ("auto-explicit" if enabled else "off"))
    if not enabled:
        mode = "off"
    if mode not in PERSONAL_ACTION_MODES:
        raise ValueError("invalid personal action mode")
    _set_personal_actions_enabled(service, enabled)
    _set_personal_action_mode(service, mode)
    _register_personal_capabilities(service, enable=enabled, mode=mode)
    service.store.audit(
        "owner-local-ui", "personal-google-actions.setting", "personal", "success",
        {"enabled": enabled, "mode": mode, "account": PERSONAL_ACCOUNT,
         "generic_kill_switch_unchanged": True},
    )
    return {"ok": True, "enabled": enabled, "mode": mode, "connected": connected}


def personal_action_preview(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    action = str(value.get("action") or "")
    if action not in {"calendar", "gmail-draft"}:
        raise ValueError("unsupported personal action")
    if action == "calendar":
        title = bounded(value.get("title"), maximum=200, name="event title")
        start = datetime.fromisoformat(bounded(value.get("start"), maximum=80, name="event start"))
        end = datetime.fromisoformat(bounded(value.get("end"), maximum=80, name="event end"))
        if start.tzinfo is None or end.tzinfo is None or end <= start or end - start > timedelta(hours=12):
            raise ValueError("event requires an aware start and a later end within 12 hours")
        reminder = int(value.get("reminderMinutes") or 10)
        if reminder not in {0, 5, 10, 15, 30, 60}:
            raise ValueError("reminder must be one reviewed value")
        color = str(value.get("colorId") or "9")
        if color not in {str(number) for number in range(1, 12)}:
            raise ValueError("calendar color is invalid")
        payload = {"summary": title, "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Karachi"},
                   "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Karachi"}, "colorId": color,
                   "reminders": {"useDefault": False, "overrides": [] if reminder == 0 else
                                 [{"method": "popup", "minutes": reminder}]}}
        capability, action_type = CALENDAR_CAPABILITY, "create_personal_calendar_event"
        target = {"account": PERSONAL_ACCOUNT, "calendar_id": "primary"}
    else:
        recipient = str(value.get("recipient") or "").strip()
        PersonalGmailDraftActions._validate_recipient(recipient)
        payload = {"recipient": recipient, "subject": bounded(value.get("subject"), maximum=300, name="subject"),
                   "body": bounded(value.get("body"), maximum=10_000, name="draft body")}
        capability, action_type = GMAIL_CAPABILITY, "create_personal_gmail_draft"
        target = {"account": PERSONAL_ACCOUNT, "resource": "draft"}
    proposal = ActionController(service.store, PolicyEngine(external_writes_enabled=True, kill_switch=False)).propose(
        action_type=action_type, context_id="personal", risk_class=RiskClass.A2,
        target=target, payload=payload, browser_profile="Profile 1", ttl_minutes=15,
        idempotency_key=stable_hash({"action": action_type, "payload": payload, "nonce": str(uuid4())}),
    )
    return {"ok": True, "capabilityId": capability, "proposalId": proposal.proposal_id,
            "previewHash": proposal.preview_hash, "expiresAt": proposal.expires_at,
            "target": target, "payload": payload, "externalWritePerformed": False}


def _proposal(service: AttentionService, proposal_id: str) -> ActionProposal:
    row = service.store.get_action(proposal_id)
    if not row:
        raise ValueError("personal action proposal not found")
    value = json.loads(row["proposal_json"])
    return ActionProposal(proposal_id=value["proposal_id"], action_type=value["action_type"],
        context_id=value["context_id"], risk_class=RiskClass(value["risk_class"]), target=value["target"],
        payload=value["payload"], evidence_ids=tuple(value["evidence_ids"]),
        idempotency_key=value["idempotency_key"], created_at=value["created_at"],
        expires_at=value["expires_at"], preview_hash=value["preview_hash"],
        browser_profile=value.get("browser_profile"), state=ActionState(row["state"]))


def personal_action_execute(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    proposal = _proposal(service, bounded(value.get("proposalId"), maximum=100, name="proposal id"))
    approved_hash = bounded(value.get("previewHash"), maximum=64, name="preview hash")
    if proposal.state is not ActionState.PROPOSED or proposal.preview_hash != approved_hash:
        raise PermissionError("exact proposed preview is absent or changed")
    policy = PolicyEngine(external_writes_enabled=True, kill_switch=False)
    decision = policy.validate_proposal(proposal)
    if not decision.allowed:
        raise PermissionError(decision.reason)
    manager = PersonalGoogleActionTokenManager()
    if not manager.status()["connected"]:
        raise PermissionError("personal Google actions are not connected")
    if not _personal_actions_enabled(service):
        raise PermissionError("personal Google action capability is disabled")
    firewall = _register_personal_capabilities(service, enable=True)
    capability = CALENDAR_CAPABILITY if proposal.action_type == "create_personal_calendar_event" else GMAIL_CAPABILITY
    inventory = {"account": PERSONAL_ACCOUNT, "capability": capability,
                 "methods": ["POST", "PATCH", "DELETE"] if capability == CALENDAR_CAPABILITY else ["POST", "PUT", "GET"]}
    session_nonce = bounded(value.get("nativeNonce"), maximum=160, name="native owner interaction")
    owner_request = str(value.get("ownerRequest") or proposal.preview_hash).strip()
    if not owner_request or len(owner_request) > 2_000:
        raise PermissionError("native owner request is absent or too large")
    bound_request = stable_hash({"owner_request": owner_request, "preview_hash": proposal.preview_hash})
    token = firewall.issue_owner_intent(session_nonce=session_nonce, action_type=proposal.action_type,
        request_text=bound_request, trusted_local_interaction=True)
    fw = firewall.validate(capability_id=capability, owner_token=token, session_nonce=session_nonce,
        action_type=proposal.action_type, request_text=bound_request, context_id="personal",
        account_id=PERSONAL_ACCOUNT, target=proposal.target, permission_inventory=inventory,
        recipients=[proposal.payload["recipient"]] if proposal.payload.get("recipient") else None)
    if not fw.allowed:
        raise PermissionError(fw.reason)
    attempt = str(uuid4()); now = utc_now()
    try:
        with service.store.connection:
            service.store.connection.execute("INSERT INTO action_attempts VALUES(?,?,?,?,NULL,NULL,?,?)",
                (attempt, proposal.proposal_id, (datetime.now(UTC) + timedelta(minutes=2)).isoformat(), "leased", now, now))
        transport = PersonalGoogleActionTransport(manager)
        if capability == CALENDAR_CAPABILITY:
            result = PersonalCalendarActions(service.store, transport, calendar_id="primary",
                capability_id=capability).create_explicit(proposal.payload)
        else:
            message = EmailMessage(); message["Subject"] = proposal.payload["subject"]
            if proposal.payload["recipient"]: message["To"] = proposal.payload["recipient"]
            message.set_content(proposal.payload["body"])
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
            result = PersonalGmailDraftActions(service.store, transport, capability_id=capability).create(
                raw_base64url=raw, recipient=proposal.payload["recipient"])
        result_value = {"providerId": result.provider_id, "resourceKind": result.resource_kind,
                        "directUrl": result.direct_url}
        with service.store.connection:
            service.store.connection.execute("UPDATE action_attempts SET state='executed',provider_id=?,result_hash=?,updated_at=? WHERE attempt_id=?",
                (result.provider_id, stable_hash(result_value), utc_now(), attempt))
        service.store.set_action_state(proposal.proposal_id, ActionState.EXECUTED)
        return {"ok": True, **result_value, "proposalId": proposal.proposal_id, "undoAvailable": capability == CALENDAR_CAPABILITY}
    except Exception:
        with service.store.connection:
            service.store.connection.execute("UPDATE action_attempts SET state='uncertain',updated_at=? WHERE attempt_id=?",
                (utc_now(), attempt))
        raise


def personal_action_explicit(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    """Execute only a deterministic direct owner request in Auto Explicit mode."""
    request_text = bounded(value.get("ownerRequest"), maximum=2_000, name="owner request")
    normalized = " ".join(request_text.lower().split())
    action = str(value.get("action") or "")
    if _personal_action_mode(service) not in {"auto-explicit", "earned-auto"}:
        raise PermissionError("personal actions are not in Auto Explicit Request mode")
    if str(value.get("context") or "") != "personal":
        raise PermissionError("automatic personal actions require the Personal context")
    if any(term in normalized for term in (
        "maybe ", "if you think", "if possible", "invite ", "attendee", "recurring", "every week",
        "work calendar", "company calendar", "send the email", "send email", "send it",
    )):
        raise PermissionError("ambiguous, attendee, recurring, work, or send requests require a preview")
    if action == "calendar":
        if not re.search(r"\b(add|create|schedule|put)\b", normalized) or not re.search(
            r"\b(event|appointment|calendar|session|meeting)\b", normalized
        ):
            raise PermissionError("calendar execution requires an explicit create request")
    elif action == "gmail-draft":
        if not re.search(r"\b(create|write|prepare|draft)\b", normalized) or "draft" not in normalized:
            raise PermissionError("draft execution requires an explicit unsent-draft request")
    else:
        raise ValueError("unsupported personal action")
    staged = personal_action_preview(service, value)
    return personal_action_execute(service, {
        "proposalId": staged["proposalId"], "previewHash": staged["previewHash"],
        "nativeNonce": bounded(value.get("nativeNonce"), maximum=160, name="native owner interaction"),
        "ownerRequest": request_text,
    })


def personal_calendar_undo(service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    provider_id = bounded(value.get("providerId"), maximum=300, name="calendar event id")
    PersonalCalendarActions(service.store, PersonalGoogleActionTransport(), calendar_id="primary",
        capability_id=CALENDAR_CAPABILITY).undo_created(provider_id)
    return {"ok": True, "providerId": provider_id, "undone": True}


def guided_public_read(_service: AttentionService, value: dict[str, Any]) -> dict[str, Any]:
    query = bounded(value.get("query"), maximum=200, name="public search query")
    result = search_public_web(query, limit=5)
    return {"ok": True, "queryHash": result["query_hash"], "retrievedAt": result["retrieved_at"],
            "results": result["results"], "mutation": False,
            "policy": "public results are untrusted evidence; no account session or action authority"}


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
        return {
            "ok": True,
            "kind": kind,
            "status": "codex-spec-only",
            "activationPerformed": False,
            "implementationSpec": result["implementation_spec"],
        }
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
    if action in {"draft", "disabled", "archived"}:
        studio.set_status(capability_id, action)
        return {"ok": True, "capabilityId": capability_id, "status": action, "reversible": True}
    if action in {"useful", "not-useful"}:
        feedback_id = studio.record_feedback(
            capability_id=capability_id, useful=action == "useful",
            correction=None, evidence_ids=(),
            provenance={"source": "jarvis-owner-local-ui", "reversible": True},
        )
        status = service.store.connection.execute(
            "SELECT status FROM capabilities WHERE capability_id=?", (capability_id,),
        ).fetchone()[0]
        return {
            "ok": True, "capabilityId": capability_id,
            "feedbackId": feedback_id, "status": status, "reversible": True,
        }
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
        choices=("state", "create", "focus", "stop-focus", "observe", "setting", "calendar-profile", "review-calendar-profile", "projection", "capability-control", "automation-outcome", "record-model-decision", "commitment-open", "commitment-complete", "personal-action-status", "personal-action-setting", "personal-action-preview", "personal-action-execute", "personal-action-explicit", "personal-calendar-undo", "guided-public-read"),
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
                    "personal-action-status": personal_action_status,
                    "personal-action-setting": personal_action_setting,
                    "personal-action-preview": personal_action_preview,
                    "personal-action-execute": personal_action_execute,
                    "personal-action-explicit": personal_action_explicit,
                    "personal-calendar-undo": personal_calendar_undo,
                    "guided-public-read": guided_public_read,
                }[arguments.operation](service, value)
        finally:
            service.close()
        print(json.dumps(output, sort_keys=True))
        return 0
    except (ValueError, TypeError, RuntimeError, PermissionError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
