from __future__ import annotations

from datetime import UTC, datetime
from contextlib import contextmanager
import json
from types import SimpleNamespace
import unittest

from hermes_attention.action_firewall import ActionFirewall
from hermes_attention.automation_miner import AutomationMiner
from hermes_attention.calendar_style import CalendarStyleProfiler
from hermes_attention.capabilities import CapabilityStudio
from hermes_attention.computer_awareness import AwarenessPolicy, ComputerAwareness
from hermes_attention.domain import ContextLabel, EvidenceItem, Provenance
from hermes_attention.model_governor import ModelGovernor, ModelSignals
from hermes_attention.models import ModelRouter
from hermes_attention.personal_google_actions import PersonalCalendarActions, PersonalGmailDraftActions
from hermes_attention.projects import Portfolio, RadarRegistry
from hermes_attention.proactive import ProactiveChiefOfStaff
from hermes_attention.storage import Store
from hermes_attention.work_ledger import LedgerEntryInput, WorkLedger
from scripts.jarvis_local_state import commitment_complete, commitment_open


@contextmanager
def raises(error_type: type[BaseException]):
    try:
        yield
    except error_type:
        return
    raise AssertionError(f"expected {error_type.__name__}")


def evidence(evidence_id: str, context_id: str, content: str = "project update") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        title=content,
        content=content,
        provenance=Provenance(
            source_system="test", connection_id="fixture", source_id=evidence_id,
            source_timestamp="2026-08-12T01:00:00+00:00", retrieved_at="2026-08-12T01:01:00+00:00",
        ),
        contexts=(ContextLabel(context_id, 1.0, "fixture", "test"),),
    )


def test_work_ledger_is_idempotent_and_uses_context_local_date() -> None:
    with Store(":memory:") as store:
        store.add_evidence(evidence("e1", "inside-success"))
        ledger = WorkLedger(store)
        item = LedgerEntryInput(
            kind="task", occurred_at_utc="2026-08-12T02:30:00+00:00",
            context_id="inside-success", summary="Worked on Jarvis", evidence_ids=("e1",),
            actor_id="Syed", actor_state="verified",
        )
        first, inserted = ledger.record(item)
        second, inserted_again = ledger.record(item)
        assert first == second
        assert inserted is True and inserted_again is False
        assert ledger.query(context_id="inside-success", local_date="2026-08-11")[0]["actor_id"] == "Syed"
        assert ledger.query(context_id="mitchell") == []
        with raises(ValueError):
            ledger.record(LedgerEntryInput("task", item.occurred_at_utc, "unknown", "x", ("e1",)))


def test_search_filters_context_before_limit() -> None:
    with Store(":memory:") as store:
        for number in range(15):
            store.add_evidence(evidence(f"wrong-{number}", "personal", "needle needle needle"))
        store.add_evidence(evidence("right", "inside-success", "needle"))
        results = store.search_evidence("needle", context_id="inside-success", limit=1)
        assert [item["evidence_id"] for item in results] == ["right"]


def test_work_ledger_refresh_is_bounded_and_incremental() -> None:
    with Store(":memory:") as store:
        for index in range(3):
            item = evidence(f"refresh-{index}", "personal", f"Ledger item {index}")
            item = EvidenceItem(
                evidence_id=item.evidence_id, title=item.title, content=item.content,
                provenance=Provenance(
                    source_system="codex", connection_id="codex-local", source_id=item.evidence_id,
                    source_timestamp=f"2026-08-0{index + 1}T12:00:00+00:00",
                    retrieved_at=f"2026-08-0{index + 1}T12:01:00+00:00",
                ),
                contexts=item.contexts,
            )
            store.add_evidence(item)
        ledger = WorkLedger(store)
        first = ledger.refresh_from_evidence(limit=2)
        second = ledger.refresh_from_evidence(limit=2)
        third = ledger.refresh_from_evidence(limit=2)
        assert first["processed"] == 2 and first["has_more"] is True
        assert second["processed"] == 1
        assert third["processed"] == 0
        rows = ledger.query(context_id="personal", limit=10)
        assert len(rows) == 3
        assert all(row["actor_state"] == "owner" for row in rows)


def test_model_governor_route_matrix_and_no_sol() -> None:
    config = {
        "default_route": "routine",
        "budget_usd": {"soft": 10, "hard": 20},
        "routes": {
            route: {"provider": "openai" if route in {"vision", "review"} else "deepseek",
                    "model": route, "purpose": route, "enabled": True}
            for route in ("routine", "difficult", "vision", "review")
        },
    }
    with Store(":memory:") as store:
        governor = ModelGovernor(ModelRouter(config, store), store)
        assert governor.decide(ModelSignals()).route == "routine"
        assert governor.decide(ModelSignals(source_count=2)).route == "difficult"
        assert governor.decide(ModelSignals(visual=True, high_stakes=True)).route == "vision"
        high = governor.decide(ModelSignals(high_stakes=True))
        assert high.route == "difficult" and high.reviewer_route == "review"
        with raises(ValueError):
            governor.decide(ModelSignals(user_override="sol"))


def test_capability_studio_intersects_tools_and_rejects_protected_fields() -> None:
    with Store(":memory:") as store:
        studio = CapabilityStudio(store, {"search_evidence"})
        bad = studio.validate({"kind": "workflow", "context_id": "personal", "tools": ["send_email"]})
        assert bad.allowed is False
        protected = studio.validate({"kind": "workflow", "context_id": "personal", "oauth_scopes": ["mail"]})
        assert protected.allowed is False
        created = studio.create(
            {"kind": "workflow", "context_id": "personal", "tools": ["search_evidence"]},
            permission_inventory={"search_evidence": "read"},
        )
        dry = studio.dry_run(created["capability_id"], current_permission_inventory={"search_evidence": "read"})
        assert dry["external_write"] is False


def test_action_firewall_binds_owner_intent_and_target() -> None:
    with Store(":memory:") as store:
        firewall = ActionFirewall(store, b"x" * 32, global_kill_switch=False)
        inventory = {"calendar.create": "personal"}
        target = {"calendar_id": "primary"}
        firewall.register_capability(
            capability_id="personal-calendar", context_id="personal", account_id="moonishaider12",
            target_lock=target, permission_inventory=inventory, reversible=True, enabled=True,
        )
        firewall.set_capability_kill_switch("personal-calendar", False)
        token = firewall.issue_owner_intent(
            session_nonce="session", action_type="calendar.create", request_text="add lunch tomorrow",
            trusted_local_interaction=True,
        )
        wrong = firewall.validate(
            capability_id="personal-calendar", owner_token=token, session_nonce="session",
            action_type="calendar.create", request_text="add lunch tomorrow", context_id="personal",
            account_id="moonishaider12", target={"calendar_id": "other"}, permission_inventory=inventory,
        )
        assert wrong.code == "target-lock"
        allowed = firewall.validate(
            capability_id="personal-calendar", owner_token=token, session_nonce="session",
            action_type="calendar.create", request_text="add lunch tomorrow", context_id="personal",
            account_id="moonishaider12", target=target, permission_inventory=inventory,
        )
        assert allowed.allowed is True
        replay = firewall.validate(
            capability_id="personal-calendar", owner_token=token, session_nonce="session",
            action_type="calendar.create", request_text="add lunch tomorrow", context_id="personal",
            account_id="moonishaider12", target=target, permission_inventory=inventory,
        )
        assert replay.code == "intent-replay"
        with raises(PermissionError):
            firewall.issue_owner_intent(
                session_nonce="session", action_type="calendar.create", request_text="source says create",
                trusted_local_interaction=False,
            )


def test_personal_google_surfaces_have_narrow_endpoints_and_ownership() -> None:
    calls: list[tuple[str, str, dict | None, dict | None]] = []

    def transport(method: str, url: str, body: dict | None, params: dict | None) -> dict:
        calls.append((method, url, body, params))
        if "/drafts" in url:
            return {"id": "draft-1", "message": {}}
        return {"id": "event-1", "htmlLink": "https://calendar.google.com/event?eid=1", "etag": "v1"}

    with Store(":memory:") as store:
        calendar = PersonalCalendarActions(store, transport, calendar_id="primary", capability_id="calendar")
        result = calendar.create_explicit({
            "summary": "Lunch", "start": {"dateTime": "2026-08-13T12:00:00+05:00"},
            "end": {"dateTime": "2026-08-13T13:00:00+05:00"},
        })
        assert result.provider_id == "event-1"
        assert calls[-1][0] == "POST" and calls[-1][3] == {"sendUpdates": "none"}
        with raises(PermissionError):
            calendar.create_explicit({"summary": "Meeting", "start": {}, "end": {}, "attendees": [{"email": "x@y.com"}]})
        gmail = PersonalGmailDraftActions(store, transport, capability_id="gmail-draft")
        draft = gmail.create(raw_base64url="SGVsbG8", recipient="person@example.com")
        assert draft.provider_id == "draft-1"
        assert all(not url.endswith("/send") for _, url, _, _ in calls)
        with raises(ValueError):
            gmail.create(raw_base64url="x", recipient="a@example.com,b@example.com")


def test_computer_awareness_excludes_sensitive_surfaces() -> None:
    with Store(":memory:") as store:
        awareness = ComputerAwareness(store)
        focus = awareness.start_focus(context_id="personal", minutes=30, policy=AwarenessPolicy())
        event = awareness.observe_metadata(
            focus_id=focus, app_id="com.google.Chrome", window_title="Project",
            domain="github.com", browser_profile="Profile 1", context_id="personal",
        )
        assert event
        with raises(PermissionError):
            awareness.observe_metadata(
                focus_id=focus, app_id="com.1password.1password", window_title="Vault",
                domain=None, browser_profile=None, context_id="personal",
            )


def test_mitchell_project_is_dormant_not_deleted() -> None:
    with Store(":memory:") as store:
        portfolio = Portfolio(store)
        portfolio.upsert_project(
            project_id="mitchell", context_id="mitchell", name="Mitchell",
            objective="Preserve completed client context", completion_contract="Owner reactivates",
            phase="paused", lifecycle="dormant",
        )
        row = store.connection.execute("SELECT lifecycle FROM projects WHERE project_id='mitchell'").fetchone()
        assert row["lifecycle"] == "dormant"
        assert portfolio.list_active("mitchell") == []


def test_radar_only_flags_change_after_baseline() -> None:
    with Store(":memory:") as store:
        radar = RadarRegistry(store)
        radar_id = radar.create(
            context_id="personal", question="Has the tax deadline changed?", sources=["official-web"],
            cadence="weekly", material_change={"deadline": True},
        )
        assert radar.record_run(radar_id, "a", ()) is False
        assert radar.record_run(radar_id, "a", ()) is False
        assert radar.record_run(radar_id, "b", ()) is True


def test_proactive_modes_and_verified_commitment_use_one_ledger() -> None:
    with Store(":memory:") as store:
        for identifier, title in (("meeting", "Daily meeting"), ("work", "Built ledger"), ("done", "Completion proof")):
            store.add_evidence(evidence(identifier, "inside-success", title))
        ledger = WorkLedger(store)
        ledger.record(LedgerEntryInput(
            "meeting", "2026-08-12T13:00:00+00:00", "inside-success", "Daily meeting", ("meeting",),
        ))
        ledger.record(LedgerEntryInput(
            "work", "2026-08-12T14:00:00+00:00", "inside-success", "Built ledger", ("work",),
            actor_id="Syed", actor_state="owner",
        ))
        task_id = ledger.open_commitment(
            title="Finish ledger", context_id="inside-success", evidence_ids=("work",),
        )
        ledger.verify_commitment_complete(task_id, evidence_id="done")
        assert store.connection.execute("SELECT status FROM tasks WHERE task_id=?", (task_id,)).fetchone()[0] == "completed"
        chief = ProactiveChiefOfStaff(ledger)
        end = chief.end_of_day(context_id="inside-success", local_date="2026-08-12")
        assert end["dloa"]["meetings_first"][0]["kind"] == "meeting"
        assert end["dloa"]["text"].startswith("```\nDLOA – 12 Aug 2026\n• Daily meeting.")
        assert end["dloa"]["external_send"] is False
        assert chief.start_of_day(context_id="mitchell", local_date="2026-08-12")["source_count"] == 0


def test_jarvis_commitment_controls_require_same_context_ledger_evidence() -> None:
    with Store(":memory:") as store:
        for identifier, context_id in (("source", "inside-success"), ("done", "inside-success"), ("wrong", "personal")):
            store.add_evidence(evidence(identifier, context_id, identifier))
        ledger = WorkLedger(store)
        ledger.record(LedgerEntryInput("work", "2026-08-12T14:00:00+00:00", "inside-success", "Source", ("source",)))
        ledger.record(LedgerEntryInput("work", "2026-08-12T15:00:00+00:00", "inside-success", "Done", ("done",)))
        ledger.record(LedgerEntryInput("work", "2026-08-12T16:00:00+00:00", "personal", "Wrong", ("wrong",)))
        service = SimpleNamespace(store=store, ledger=ledger)
        opened = commitment_open(service, {
            "context": "inside-success", "title": "Finish the verified item", "evidenceId": "source",
        })
        with raises(ValueError):
            commitment_complete(service, {"taskId": opened["taskId"], "evidenceId": "wrong"})
        completed = commitment_complete(service, {"taskId": opened["taskId"], "evidenceId": "done"})
        assert completed["status"] == "completed"
        assert completed["externalWrite"] is False


def test_dloa_replaces_codex_role_labels_with_bounded_activity() -> None:
    with Store(":memory:") as store:
        item = evidence(
            "codex-work", "inside-success",
            "Implemented the performance analyzer checks and verified the safe rollout.\nRank reps relative to one another.",
        )
        item = EvidenceItem(
            evidence_id=item.evidence_id,
            title="Magic Mike -1 — assistant",
            content=item.content,
            provenance=Provenance(
                source_system="codex", connection_id="codex-local", source_id=item.evidence_id,
                source_timestamp="2026-08-12T01:00:00+00:00", retrieved_at="2026-08-12T01:01:00+00:00",
            ),
            contexts=item.contexts,
        )
        store.add_evidence(item)
        ledger = WorkLedger(store)
        ledger.record(LedgerEntryInput(
            "work", "2026-08-12T01:00:00+00:00", "inside-success",
            "Magic Mike -1 — assistant", (item.evidence_id,), actor_id="Codex for Syed", actor_state="owner",
        ))
        output = ProactiveChiefOfStaff(ledger).end_of_day(
            context_id="inside-success", local_date="2026-08-11",
        )["dloa"]["text"]
        assert "Worked on the reps' performance analyzer system." in output
        assert " — assistant" not in output and " — user" not in output
        assert "Rank reps" not in output


def test_automation_miner_requires_three_evidenced_occurrences_and_tracks_outcome() -> None:
    with Store(":memory:") as store:
        for index in range(3):
            store.add_evidence(evidence(f"repeat-{index}", "personal", "Repeated report cleanup"))
        miner = AutomationMiner(store)
        for index in range(3):
            miner.observe(
                context_id="personal", signature="clean-report", description="Clean report",
                duration_minutes=10, evidence_ids=(f"repeat-{index}",),
                occurred_at=f"2026-08-{10 + index:02d}T12:00:00+00:00",
            )
            if index < 2:
                assert miner.propose(context_id="personal", signature="clean-report") is None
        proposal = miner.propose(context_id="personal", signature="clean-report")
        assert proposal and proposal["occurrence_count"] == 3
        miner.record_outcome(proposal["proposal_id"], "rejected")
        row = store.connection.execute(
            "SELECT status,false_alerts FROM automation_proposals WHERE proposal_id=?",
            (proposal["proposal_id"],),
        ).fetchone()
        assert dict(row) == {"status": "rejected", "false_alerts": 1}


def test_feedback_demotes_capability_and_is_inspectable() -> None:
    with Store(":memory:") as store:
        studio = CapabilityStudio(store, {"search_evidence"})
        created = studio.create(
            {"kind": "workflow", "context_id": "personal", "tools": ["search_evidence"]},
            permission_inventory={"search_evidence": "read"},
        )
        studio.set_status(created["capability_id"], "active")
        feedback_id = studio.record_feedback(
            capability_id=created["capability_id"], useful=False,
            correction="Use a shorter format", evidence_ids=(),
            provenance={"source": "trusted-local-owner-interaction"},
        )
        assert feedback_id
        assert store.connection.execute(
            "SELECT status FROM capabilities WHERE capability_id=?", (created["capability_id"],),
        ).fetchone()[0] == "disabled"


def test_calendar_style_profile_is_bounded_and_owner_reviewable() -> None:
    events = [{
        "summary": f"Planning {index}", "colorId": "2",
        "start": {"dateTime": f"2026-08-{index + 1:02d}T10:00:00+05:00"},
        "end": {"dateTime": f"2026-08-{index + 1:02d}T10:30:00+05:00"},
        "reminders": {"useDefault": True},
    } for index in range(6)]
    with Store(":memory:") as store:
        profiler = CalendarStyleProfiler(store)
        result = profiler.derive(
            account_id="personal", calendar_id="primary", events=events,
            window_start="2026-02-01", window_end="2026-08-12",
        )
        assert result["profile"]["median_timed_duration_minutes"] == 30
        reviewed = profiler.review(result["profile_id"], corrections={"conflict_and_buffer_preferences": "15-minute buffer"})
        assert reviewed["review_status"] == "owner-reviewed"


def test_focus_timeline_and_mutating_navigation_fail_to_preview() -> None:
    with Store(":memory:") as store:
        awareness = ComputerAwareness(store)
        focus = awareness.start_focus(context_id="personal", minutes=30, policy=AwarenessPolicy())
        awareness.observe_metadata(
            focus_id=focus, app_id="com.google.Chrome", window_title="Project",
            domain="github.com", browser_profile="Profile 1", context_id="personal",
        )
        timeline = awareness.timeline(focus)
        assert timeline["events"][0]["browser_profile"] == "Profile 1"
        assert timeline["screenshots_retained"] == 0
        navigation = awareness.stage_navigation(
            focus_id=focus, action_type="scroll", target={"domain": "github.com"},
        )
        assert navigation["mutation"] is False
        staged = awareness.stage_navigation(
            focus_id=focus, action_type="type", target={"domain": "example.com"}, payload={"text": "hello"},
        )
        assert staged["mode"] == "preview" and staged["execution_performed"] is False


class Prompt7CoreTests(unittest.TestCase):
    def test_work_ledger(self) -> None:
        test_work_ledger_is_idempotent_and_uses_context_local_date()

    def test_context_search(self) -> None:
        test_search_filters_context_before_limit()

    def test_ledger_refresh(self) -> None:
        test_work_ledger_refresh_is_bounded_and_incremental()

    def test_model_governor(self) -> None:
        test_model_governor_route_matrix_and_no_sol()

    def test_capability_studio(self) -> None:
        test_capability_studio_intersects_tools_and_rejects_protected_fields()

    def test_action_firewall(self) -> None:
        test_action_firewall_binds_owner_intent_and_target()

    def test_personal_google(self) -> None:
        test_personal_google_surfaces_have_narrow_endpoints_and_ownership()

    def test_computer_awareness(self) -> None:
        test_computer_awareness_excludes_sensitive_surfaces()

    def test_mitchell_dormancy(self) -> None:
        test_mitchell_project_is_dormant_not_deleted()

    def test_radar_change_detection(self) -> None:
        test_radar_only_flags_change_after_baseline()

    def test_proactive_and_commitments(self) -> None:
        test_proactive_modes_and_verified_commitment_use_one_ledger()
        test_jarvis_commitment_controls_require_same_context_ledger_evidence()

    def test_dloa_activity_summary(self) -> None:
        test_dloa_replaces_codex_role_labels_with_bounded_activity()

    def test_automation_miner(self) -> None:
        test_automation_miner_requires_three_evidenced_occurrences_and_tracks_outcome()

    def test_behavior_feedback(self) -> None:
        test_feedback_demotes_capability_and_is_inspectable()

    def test_calendar_style(self) -> None:
        test_calendar_style_profile_is_bounded_and_owner_reviewable()

    def test_focus_timeline(self) -> None:
        test_focus_timeline_and_mutating_navigation_fail_to_preview()
