"""The generated staff summary is visible only in the local staff interface."""

import pytest
from streamlit.testing.v1 import AppTest

import caregiver_view
from coordinator import coordinate_visit
from staff_tasks import list_mock_staff_tasks


@pytest.mark.parametrize("writer_fails", [False, True])
def test_caregiver_report_reaches_visible_staff_summary(tmp_path, monkeypatch, logistics_review_state, staff_summary_draft, writer_fails):
    queue = tmp_path / "queue.json"
    monkeypatch.setenv("VISITREADY_STAFF_QUEUE_PATH", str(queue))
    monkeypatch.setenv("VISITREADY_RUN_HISTORY_PATH", str(tmp_path / "history.json"))
    def writer(state):
        if writer_fails:
            raise ValueError("Simulated unavailable writer")
        return staff_summary_draft
    def controlled_coordinate(appointment, message):
        return coordinate_visit(
            appointment, message,
            readiness_role=lambda *args: logistics_review_state.readiness_proposal,
            communication_role=writer,
            routing_role=lambda *args: (_ for _ in ()).throw(AssertionError("Do not look up public sources on this review case")),
        )
    monkeypatch.setattr(caregiver_view, "coordinate_visit", controlled_coordinate)
    caregiver = AppTest.from_file("app.py").run(timeout=15)
    caregiver.text_area(key="caregiver_message").set_value(logistics_review_state.caregiver_message).run()
    next(button for button in caregiver.button if button.label == "Ask VisitReady").click().run()
    assert not caregiver.exception
    assert staff_summary_draft.summary not in " ".join(item.value for item in caregiver.markdown)
    tasks = list_mock_staff_tasks(queue_path=queue)
    assert len(tasks) == 1
    assert tasks[0].summary_source == ("template" if writer_fails else "ai_draft")
    team = AppTest.from_file("pages/1_Staff_Demo.py").run(timeout=15)
    assert not team.exception
    visible_text = " ".join(item.value for item in team.text)
    assert tasks[0].staff_summary.summary in visible_text
    assert logistics_review_state.caregiver_message in visible_text
    label = "Basic staff summary" if writer_fails else "AI staff summary"
    assert label in " ".join(item.value for item in team.markdown)
    next(button for button in team.button if button.label == "Mark seen in demo").click().run()
    assert not team.exception
    assert list_mock_staff_tasks(queue_path=queue)[0].status == "seen_in_demo"
