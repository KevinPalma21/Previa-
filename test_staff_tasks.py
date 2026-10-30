"""The mock queue tracks acknowledgement without claiming clinical review."""

import pytest

from models import ReviewRequest
from staff_tasks import create_mock_staff_task, list_mock_staff_tasks, mark_mock_task_seen


def test_seen_task_keeps_its_history_and_new_question_gets_new_task(tmp_path):
    queue_path = tmp_path / "staff_tasks.json"
    question = "What medicine should I give my child?"
    review = ReviewRequest(
        appointment_id="DEMO-001",
        summary="Clinical question requires staff review.",
        caregiver_message=question,
        unresolved_items=[],
        caregiver_confirmed=True,
    )

    first = create_mock_staff_task(review, "clinical_question", queue_path=queue_path)
    seen = mark_mock_task_seen(first.task_id, queue_path=queue_path)
    seen_again = mark_mock_task_seen(first.task_id, queue_path=queue_path)
    second = create_mock_staff_task(review, "clinical_question", queue_path=queue_path)
    tasks = list_mock_staff_tasks(queue_path=queue_path)

    assert seen.status == "seen_in_demo"
    assert seen.seen_at is not None
    assert seen_again.seen_at == seen.seen_at
    assert second.task_id != first.task_id
    assert [task.status for task in tasks] == ["seen_in_demo", "awaiting_staff_review"]
    assert tasks[0].original_message == question
    assert tasks[1].original_message == question
    assert tasks[0].assigned_team == "Appointment care team (demo)"


def test_unknown_task_cannot_be_marked_seen(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        mark_mock_task_seen("VR-NOTFOUND", queue_path=tmp_path / "staff_tasks.json")
