"""Clinical questions stop before AI and need an explicit handoff request."""

import pytest

from caregiver_response import compose_caregiver_response
from clinical_gate import needs_clinical_review, pre_model_route
from coordinator import coordinate_visit, submit_clinical_review
from staff_tasks import create_mock_staff_task, list_mock_staff_tasks
from tools import get_appointment


@pytest.mark.parametrize(
    "message",
    [
        "What medicine should I give my child?",
        "Should my daughter take her medication before the appointment?",
        "Can I stop the antibiotic?",
        "How much Tylenol do I give?",
        "My ride fell through and my child has a fever.",
    ],
)
def test_obvious_clinical_questions_are_flagged(message):
    assert needs_clinical_review(message)


@pytest.mark.parametrize(
    "message", ["What should I bring?", "My ride fell through."]
)
def test_logistics_messages_are_not_flagged(message):
    assert not needs_clinical_review(message)
    assert pre_model_route(message) == "logistics"


def test_recognized_medicine_name_without_logistics_cue_still_gets_review():
    assert pre_model_route("Is Zyrtec okay before my appointment?") == "clinical_review"


def test_clinical_route_calls_no_agents_and_waits_for_explicit_submission(tmp_path):
    queue_path = tmp_path / "staff_tasks.json"
    question = "What medicine should I give my child?"

    def agent_must_not_run(*args, **kwargs):
        raise AssertionError("An AI role ran after the clinical gate")

    def run():
        return coordinate_visit(
            get_appointment("DEMO-001", use_saved=False),
            question,
            readiness_role=agent_must_not_run,
            routing_role=agent_must_not_run,
            resource_role=agent_must_not_run,
            communication_role=agent_must_not_run,
            staff_task_role=lambda review, category: create_mock_staff_task(
                review, category, queue_path=queue_path
            ),
        )

    plan = run()
    response = compose_caregiver_response(plan)
    assert plan.case_state.staff_task is None
    assert not queue_path.exists()
    assert "care team review" in response.next_step
    plan = submit_clinical_review(
        plan, confirmed=True,
        staff_task_role=lambda review, category: create_mock_staff_task(
            review, category, queue_path=queue_path
        ),
    )
    repeated_plan = submit_clinical_review(
        run(), confirmed=True,
        staff_task_role=lambda review, category: create_mock_staff_task(
            review, category, queue_path=queue_path
        ),
    )
    response = compose_caregiver_response(plan)
    saved = queue_path.read_text(encoding="utf-8")

    assert plan.policy_result == "human_review"
    assert plan.case_state.clinical_gate_triggered
    assert plan.case_state.completed_roles == []
    assert plan.case_state.staff_task.category == "clinical_question"
    assert repeated_plan.case_state.staff_task.task_id == plan.case_state.staff_task.task_id
    assert len(list_mock_staff_tasks(queue_path=queue_path)) == 1
    assert question in saved
    assert plan.case_state.staff_task.original_message == question
    assert plan.case_state.staff_task.assigned_team == "Appointment care team (demo)"
    assert "tylenol" not in response.next_step.lower()
    assert "awaiting care team review" in response.next_step.lower()
    assert "demo" not in response.next_step.lower()
    assert response.mock_staff_task_id == plan.case_state.staff_task.task_id


def test_queue_failure_does_not_claim_a_task_was_created():
    def failing_queue(review, category):
        raise OSError("Demo queue unavailable")

    plan = coordinate_visit(
        get_appointment("DEMO-001", use_saved=False),
        "Should I take this medication?",
        staff_task_role=failing_queue,
    )
    plan = submit_clinical_review(plan, confirmed=True, staff_task_role=failing_queue)
    response = compose_caregiver_response(plan)

    assert plan.case_state.completed_roles == []
    assert plan.case_state.staff_task is None
    assert plan.case_state.staff_task_error == "OSError"
    assert response.mock_staff_task_id is None
    assert "mock task" not in response.next_step.lower()
    assert "nothing has been submitted" in response.next_step.lower()


def test_named_medicine_question_calls_no_ai_and_gets_clinical_review(tmp_path):
    def agent_must_not_run(*args, **kwargs):
        raise AssertionError("An AI role ran on an out-of-scope question")

    plan = coordinate_visit(
        get_appointment("DEMO-001", use_saved=False),
        "Is Zyrtec okay before my appointment?",
        readiness_role=agent_must_not_run,
        routing_role=agent_must_not_run,
        resource_role=agent_must_not_run,
        communication_role=agent_must_not_run,
        staff_task_role=lambda review, category: create_mock_staff_task(
            review, category, queue_path=tmp_path / "staff_tasks.json"
        ),
    )

    response = compose_caregiver_response(plan)
    assert plan.case_state.completed_roles == []
    assert plan.case_state.pre_model_review_reason == "clinical_review"
    assert plan.case_state.staff_task is None
    assert "care team review" in response.next_step.lower()
    assert "zyrtec" not in response.next_step.lower()
