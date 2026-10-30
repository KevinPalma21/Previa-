"""End-to-end local handoff behavior with controlled AI roles and temporary queues."""

import json

import pytest

from caregiver_response import compose_caregiver_response
from coordinator import coordinate_visit, submit_clinical_review
from models import ReviewRequest
from run_history import record_run
from staff_tasks import create_mock_staff_task, list_mock_staff_tasks, mark_mock_task_seen
from tools import get_appointment


def run_review(state, writer, queue_path):
    def skipped(*args):
        raise AssertionError("The logistics-review route must skip public-information roles")
    return coordinate_visit(
        state.appointment, state.caregiver_message,
        readiness_role=lambda *args: state.readiness_proposal,
        routing_role=skipped, resource_role=skipped,
        communication_role=writer,
        staff_task_role=lambda review, category: create_mock_staff_task(review, category, queue_path=queue_path),
    )


def test_ai_summary_survives_reload_and_never_changes_appointment_or_caregiver_reply(tmp_path, logistics_review_state, staff_summary_draft):
    before = logistics_review_state.appointment.model_dump()
    queue = tmp_path / "queue.json"
    plan = run_review(logistics_review_state, lambda state: staff_summary_draft, queue)
    task = list_mock_staff_tasks(queue_path=queue)[0]
    assert task.staff_summary == staff_summary_draft
    assert task.summary_source == "ai_draft"
    assert task.original_message == logistics_review_state.caregiver_message
    assert "uncertain" in task.staff_summary.reported_details[2].statement
    assert "don't know" in task.staff_summary.reported_details[2].source_quote
    response = compose_caregiver_response(plan)
    assert staff_summary_draft.summary not in response.next_step
    assert "care-team review queue" in response.next_step
    assert logistics_review_state.appointment.model_dump() == before
    assert plan.case_state.appointment.model_dump() == before
    assert not (tmp_path / "appointment.json").exists()
    seen = mark_mock_task_seen(task.task_id, queue_path=queue)
    assert seen.staff_summary == task.staff_summary
    assert seen.original_message == task.original_message


def test_invalid_ai_evidence_is_replaced_not_saved(tmp_path, logistics_review_state, staff_summary_draft):
    staff_summary_draft.reported_details[0].source_quote = "Invented caregiver statement"
    plan = run_review(logistics_review_state, lambda state: staff_summary_draft, tmp_path / "queue.json")
    assert plan.policy_result == "human_review"
    assert plan.case_state.communication_decision.result == "use_fallback"
    task = plan.case_state.staff_task
    assert task.summary_source == "template"
    assert "Invented" not in task.model_dump_json()
    assert task.staff_summary.reported_details[0].source_quote == "My ride fell through."


def test_logistics_review_is_decided_before_communication_and_queued_after_checks(tmp_path, logistics_review_state, staff_summary_draft):
    calls = []
    def readiness(*args):
        calls.append("readiness")
        return logistics_review_state.readiness_proposal
    def writer(state):
        assert state.policy_result == "human_review"
        assert state.review_draft is not None
        calls.append("communication")
        return staff_summary_draft
    def queue(review, category):
        assert review.staff_summary == staff_summary_draft
        assert review.summary_source == "ai_draft"
        calls.append("staff_queue")
        return create_mock_staff_task(review, category, queue_path=tmp_path / "queue.json")
    def forbidden(*args):
        raise AssertionError("Logistics review must skip Orchestrator and Resource")
    plan = coordinate_visit(
        logistics_review_state.appointment, logistics_review_state.caregiver_message,
        readiness_role=readiness, communication_role=writer,
        routing_role=forbidden, resource_role=forbidden, staff_task_role=queue,
    )
    assert calls == ["readiness", "communication", "staff_queue"]
    response = compose_caregiver_response(plan)
    assert response.staff_review_needed
    assert "care-team review queue" in response.next_step
    assert "demo" not in response.next_step


def test_new_logistics_report_is_not_lost_to_pending_category_deduplication(tmp_path, logistics_review_state, staff_summary_draft):
    queue = tmp_path / "queue.json"
    first = run_review(logistics_review_state, lambda state: staff_summary_draft, queue)
    repeated = run_review(logistics_review_state, lambda state: staff_summary_draft, queue)
    assert first.case_state.staff_task.task_id == repeated.case_state.staff_task.task_id
    another = logistics_review_state.model_copy(deep=True)
    another.caregiver_message += " I also need to clarify the paperwork."
    next_plan = run_review(another, lambda state: staff_summary_draft, queue)
    assert next_plan.case_state.staff_task.task_id != first.case_state.staff_task.task_id
    assert len(list_mock_staff_tasks(queue_path=queue)) == 2


@pytest.mark.parametrize("message", ["What medicine should my child take?", "Is Zyrtec okay before my appointment?"])
def test_clinical_handoff_skips_all_ai_and_retains_exact_question_only_after_request(tmp_path, message):
    def forbidden(*args):
        raise AssertionError("No model may run on a direct-review case")
    queue = tmp_path / "queue.json"
    plan = coordinate_visit(
        get_appointment("DEMO-001", use_saved=False), message,
        readiness_role=forbidden, routing_role=forbidden, resource_role=forbidden,
        communication_role=forbidden,
        staff_task_role=lambda review, category: create_mock_staff_task(review, category, queue_path=queue),
    )
    assert plan.case_state.completed_roles == []
    assert plan.case_state.staff_task is None
    assert not queue.exists()
    plan = submit_clinical_review(
        plan, confirmed=True,
        staff_task_role=lambda review, category: create_mock_staff_task(review, category, queue_path=queue),
    )
    task = list_mock_staff_tasks(queue_path=queue)[0]
    assert task.staff_summary is None
    assert task.original_message == message
    assert plan.case_state.completed_roles == []
    assert task.summary_source is None


def test_history_records_summary_check_without_storing_model_or_caregiver_prose(tmp_path, logistics_review_state, staff_summary_draft):
    plan = run_review(logistics_review_state, lambda state: staff_summary_draft, tmp_path / "queue.json")
    history = tmp_path / "history.json"
    record = record_run(plan, "sample", history_path=history)
    outcomes = {event.step: event.outcome for event in record.events}
    assert outcomes["communication"] == "ran"
    assert outcomes["staff_summary_check"] == "passed"
    assert outcomes["mock_staff_task"] == "queued"
    assert staff_summary_draft.summary not in history.read_text(encoding="utf-8")
    assert logistics_review_state.caregiver_message not in history.read_text(encoding="utf-8")


def test_old_metadata_tasks_still_load_without_migration(tmp_path):
    path = tmp_path / "queue.json"
    path.write_text(json.dumps([{
        "task_id": "VR-OLD", "appointment_id": "DEMO-001", "category": "clinical_question",
        "status": "awaiting_staff_review", "created_at": "2026-10-01T12:00:00Z", "seen_at": None,
    }]), encoding="utf-8")
    task = list_mock_staff_tasks(queue_path=path)[0]
    assert task.staff_summary is None
    assert task.original_message is None


def test_clinical_queue_rejects_an_ai_summary(tmp_path, staff_summary_draft):
    review = ReviewRequest(appointment_id="DEMO-001", summary="Review", caregiver_message="What medicine?", unresolved_items=[], staff_summary=staff_summary_draft, summary_source="ai_draft")
    with pytest.raises(ValueError, match="Only logistics"):
        create_mock_staff_task(review, "clinical_question", queue_path=tmp_path / "queue.json")
