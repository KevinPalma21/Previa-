"""Explicit clinical handoff, route boundaries, deduplication and retry."""

import pytest
from streamlit.testing.v1 import AppTest

import caregiver_view
from coordinator import coordinate_visit, submit_clinical_review
from models import ReviewRequest
from staff_tasks import create_mock_staff_task, list_mock_staff_tasks
from tools import get_appointment


def clinical_plan(message="What medicine should my child take?"):
    def forbidden(*args, **kwargs):
        raise AssertionError("No AI or queue tool can run before the review request")
    return coordinate_visit(
        get_appointment("DEMO-001", use_saved=False), message,
        readiness_role=forbidden, routing_role=forbidden,
        resource_role=forbidden, communication_role=forbidden,
        staff_task_role=forbidden,
    )


def test_confirmation_and_screened_context_are_required(tmp_path):
    plan = clinical_plan()
    with pytest.raises(ValueError, match="caregiver must request"):
        submit_clinical_review(plan, confirmed=False)
    denied = coordinate_visit(get_appointment("DEMO-001", use_saved=False), "Solve this equation for me.")
    with pytest.raises(ValueError, match="screened clinical"):
        submit_clinical_review(denied, confirmed=True)
    tampered = plan.model_copy(deep=True)
    tampered.review_draft.caregiver_message = "A different unscreened question"
    with pytest.raises(ValueError, match="match the screened"):
        submit_clinical_review(tampered, confirmed=True)
    review = ReviewRequest(
        appointment_id="DEMO-001", summary="Review", caregiver_message="What medicine?",
        unresolved_items=[],
    )
    with pytest.raises(ValueError, match="explicit review request"):
        create_mock_staff_task(review, "clinical_question", queue_path=tmp_path / "queue.json")
    assert not (tmp_path / "queue.json").exists()


def test_different_clinical_questions_keep_distinct_tickets(tmp_path):
    queue = tmp_path / "queue.json"
    def submit(message):
        return submit_clinical_review(
            clinical_plan(message), confirmed=True,
            staff_task_role=lambda review, category: create_mock_staff_task(review, category, queue_path=queue),
        )
    first = submit("What medicine should my child take?")
    duplicate = submit("What medicine should my child take?")
    other = submit("Should I stop my child's medication?")
    assert first.case_state.staff_task.task_id == duplicate.case_state.staff_task.task_id
    assert other.case_state.staff_task.task_id != first.case_state.staff_task.task_id
    assert len(list_mock_staff_tasks(queue_path=queue)) == 2
    assert all(task.staff_summary is None for task in list_mock_staff_tasks(queue_path=queue))


def test_failed_submission_does_not_claim_success_and_can_retry(tmp_path, monkeypatch):
    queue = tmp_path / "queue.json"
    monkeypatch.setenv("VISITREADY_STAFF_QUEUE_PATH", str(queue))
    monkeypatch.setenv("VISITREADY_RUN_HISTORY_PATH", str(tmp_path / "history.json"))
    def unavailable(review, category):
        raise OSError("Simulated queue failure")
    def fail_submission(plan, *, confirmed):
        return submit_clinical_review(plan, confirmed=confirmed, staff_task_role=unavailable)
    monkeypatch.setattr(caregiver_view, "submit_clinical_review", fail_submission)
    app = AppTest.from_file("app.py").run()
    app.text_area(key="caregiver_message").set_value("What medicine should my child take?").run()
    next(button for button in app.button if button.label == "Ask VisitReady").click().run()
    next(button for button in app.button if button.label == "Care team review").click().run()
    assert not app.exception
    assert "Nothing has been submitted" in " ".join(item.value for item in app.markdown)
    assert not app.success
    assert not queue.exists()
    assert "Care team review" in [button.label for button in app.button]
    monkeypatch.setattr(caregiver_view, "submit_clinical_review", submit_clinical_review)
    next(button for button in app.button if button.label == "Care team review").click().run()
    assert not app.exception
    assert app.success
    assert len(list_mock_staff_tasks(queue_path=queue)) == 1

