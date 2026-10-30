"""A lost ride must reach the local staff-review path even if the model asks a question."""

from coordinator import coordinate_visit
from models import NextStep, ProposedUpdate
from staff_tasks import create_mock_staff_task
from tools import get_appointment
from visit_state import ResourceRoute


def test_unavailable_transportation_escalates_without_changing_appointment(tmp_path):
    appointment = get_appointment("DEMO-001", use_saved=False)
    original = appointment.model_dump()
    message = "My ride fell through."

    plan = coordinate_visit(
        appointment,
        message,
        readiness_role=lambda case, text: NextStep(
            action="ask_question",
            reason="The caregiver reported losing their ride.",
            message="Do you have another ride?",
            proposed_update=ProposedUpdate(
                item="transportation", status="unavailable", evidence=message
            ),
        ),
        routing_role=lambda state: (_ for _ in ()).throw(
            AssertionError("Orchestrator should be skipped for human review")
        ),
        resource_role=lambda text, selected_topic: None,
        communication_role=lambda state: (_ for _ in ()).throw(
            ValueError("Simulated unavailable writer")
        ),
        staff_task_role=lambda review, category: create_mock_staff_task(
            review, category, queue_path=tmp_path / "staff_tasks.json"
        ),
    )

    assert plan.policy_result == "human_review"
    assert plan.review_draft is not None
    assert "transportation" in plan.review_draft.unresolved_items
    assert plan.case_state.staff_task.category == "visit_logistics"
    assert appointment.model_dump() == original
