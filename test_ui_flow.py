"""A caregiver review request appears in the separate local care-team view."""

from streamlit.testing.v1 import AppTest
from html import unescape

import caregiver_view

from staff_tasks import list_mock_staff_tasks


def test_caregiver_question_reaches_local_team_view_without_model(tmp_path, monkeypatch):
    queue_path = tmp_path / "staff_tasks.json"
    history_path = tmp_path / "run_history.json"
    monkeypatch.setenv("VISITREADY_STAFF_QUEUE_PATH", str(queue_path))
    monkeypatch.setenv("VISITREADY_RUN_HISTORY_PATH", str(history_path))

    caregiver = AppTest.from_file("app.py").run()
    assert not caregiver.exception
    caregiver.text_area[0].set_value("Should I stop my child's medicine before the appointment?").run()
    next(button for button in caregiver.button if button.label == "Ask VisitReady").click().run()

    assert not caregiver.exception
    assert any("advise on medicines" in item.value for item in caregiver.markdown)
    assert caregiver.text_area(key="caregiver_message").value == ""
    assert [button.label for button in caregiver.button] == [
        "Find parking",
        "Care team review",
        "Ask VisitReady",
    ]
    assert not any("Local mock staff task" in item.value for item in caregiver.markdown)
    assert not queue_path.exists()
    next(button for button in caregiver.button if button.label == "Care team review").click().run()
    assert not caregiver.exception
    assert any("Submitted for care team review" in item.value for item in caregiver.success)
    tasks = list_mock_staff_tasks(queue_path=queue_path)
    assert len(tasks) == 1
    assert tasks[0].category == "clinical_question"
    assert tasks[0].status == "awaiting_staff_review"
    assert tasks[0].original_message == "Should I stop my child's medicine before the appointment?"
    assert tasks[0].assigned_team == "Appointment care team (demo)"
    assert tasks[0].task_id in " ".join(item.value for item in caregiver.markdown)
    assert "Care team review" not in [button.label for button in caregiver.button]
    caregiver.run()
    assert len(list_mock_staff_tasks(queue_path=queue_path)) == 1

    team = AppTest.from_file("pages/1_Staff_Demo.py").run()
    assert not team.exception
    assert team.title[0].value == "Care team workspace"
    assert tasks[0].original_message in " ".join(item.value for item in team.text)
    next(button for button in team.button if button.label == "Mark seen in demo").click().run()

    assert not team.exception
    assert list_mock_staff_tasks(queue_path=queue_path)[0].status == "seen_in_demo"


def test_caregiver_starts_without_sample_controls():
    caregiver = AppTest.from_file("app.py").run()

    assert not caregiver.exception
    assert caregiver.text_area[0].value == ""
    assert not any(button.label.startswith("Use sample:") for button in caregiver.button)
    assert "Choose a sample message" not in " ".join(item.value for item in caregiver.markdown)
    assert not caregiver.info


def test_successful_submission_clears_draft_without_hiding_exchange(tmp_path, monkeypatch):
    monkeypatch.setenv("VISITREADY_STAFF_QUEUE_PATH", str(tmp_path / "queue.json"))
    monkeypatch.setenv("VISITREADY_RUN_HISTORY_PATH", str(tmp_path / "history.json"))
    app = AppTest.from_file("app.py").run()
    message = "Solve this system of equations.\nX+Y=4\n3X-Y=89"
    app.text_area(key="caregiver_message").set_value(message).run()
    next(button for button in app.button if button.label == "Ask VisitReady").click().run()
    assert not app.exception
    assert app.text_area(key="caregiver_message").value == ""
    visible = unescape(" ".join(item.value for item in app.markdown))
    assert message in visible
    assert "I'm sorry, I can't help with that topic here." in visible
    app.text_area(key="caregiver_message").set_value("A new draft").run()
    assert message in unescape(" ".join(item.value for item in app.markdown))
    assert app.session_state["caregiver_plan"]["message"] == message
    assert not (tmp_path / "queue.json").exists()


def test_unsuccessful_submission_keeps_draft_for_retry(monkeypatch):
    def fail(*args):
        raise ValueError("Simulated failure")
    monkeypatch.setattr(caregiver_view, "coordinate_visit", fail)
    app = AppTest.from_file("app.py").run()
    app.text_area(key="caregiver_message").set_value("What should I bring?").run()
    next(button for button in app.button if button.label == "Ask VisitReady").click().run()
    assert not app.exception
    assert app.error
    assert app.text_area(key="caregiver_message").value == "What should I bring?"
