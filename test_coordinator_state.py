"""The case state reflects actual role calls, isolation and optional branches."""

from coordinator import coordinate_visit
from models import NextStep
from staff_tasks import create_mock_staff_task
from tools import get_appointment
from visit_state import ResourceRoute


def never_called(*args, **kwargs):
    raise AssertionError("This role must not run on this branch")


def test_preview_tracks_roles_without_calling_the_staff_writer_or_mutating_record():
    appointment = get_appointment("DEMO-001", use_saved=False)
    original = appointment.model_dump()
    def readiness(case, text):
        case.registration.status = "incomplete"
        return NextStep(action="ask_question", reason="Paperwork is unknown.", message="Have you been able to complete the paperwork?")
    plan = coordinate_visit(
        appointment, "Is there anything I should bring?",
        readiness_role=readiness,
        routing_role=lambda state: ResourceRoute(resource_topic="what_to_bring", reason="Public guidance request"),
        resource_role=lambda *args: None,
        communication_role=never_called,
    )
    assert plan.case_state.completed_roles == ["readiness", "orchestrator", "resource"]
    assert plan.case_state.communication_draft is None
    assert plan.case_state.communication_decision is None
    assert plan.case_state.appointment.model_dump() == original
    assert appointment.model_dump() == original


def test_blocked_proposal_stops_every_later_role():
    plan = coordinate_visit(
        get_appointment("DEMO-001", use_saved=False), "My ride fell through.",
        readiness_role=lambda *args: NextStep(action="ask_question", reason="", message="Unsafe proposal"),
        routing_role=never_called, resource_role=never_called, communication_role=never_called,
    )
    assert plan.policy_result == "block"
    assert plan.readiness_proposal is None
    assert plan.case_state.completed_roles == ["readiness"]


def test_logistics_review_runs_communication_and_skips_public_lookup(tmp_path, logistics_review_state, staff_summary_draft):
    plan = coordinate_visit(
        logistics_review_state.appointment, logistics_review_state.caregiver_message,
        readiness_role=lambda *args: logistics_review_state.readiness_proposal,
        routing_role=never_called, resource_role=never_called,
        communication_role=lambda state: staff_summary_draft,
        staff_task_role=lambda review, category: create_mock_staff_task(review, category, queue_path=tmp_path / "queue.json"),
    )
    assert plan.case_state.completed_roles == ["readiness", "communication"]
    assert plan.public_guidance is None
    assert plan.case_state.communication_decision.result == "allow_staff_draft"
    assert plan.case_state.staff_task.staff_summary == staff_summary_draft


def test_drafting_failure_keeps_the_review_task(tmp_path, logistics_review_state):
    def unavailable_writer(state):
        raise ValueError("No draft")
    plan = coordinate_visit(
        logistics_review_state.appointment, logistics_review_state.caregiver_message,
        readiness_role=lambda *args: logistics_review_state.readiness_proposal,
        routing_role=never_called, resource_role=never_called,
        communication_role=unavailable_writer,
        staff_task_role=lambda review, category: create_mock_staff_task(review, category, queue_path=tmp_path / "queue.json"),
    )
    assert plan.policy_result == "human_review"
    assert plan.case_state.communication_error == "ValueError"
    assert plan.case_state.communication_decision.result == "use_fallback"
    assert plan.case_state.staff_task.summary_source == "template"
    assert plan.case_state.staff_task.status == "awaiting_staff_review"
