"""Run history must describe the route without persisting question or model text."""

from coordinator import coordinate_visit, submit_clinical_review
from demo_agent import SAMPLE_CAREGIVER_MESSAGE, propose_demo_next_step
from run_history import list_run_history, record_run
from staff_tasks import create_mock_staff_task
from tools import get_appointment


def test_clinical_trace_skips_agents_and_excludes_message(tmp_path):
    appointment = get_appointment("DEMO-001", use_saved=False)
    message = "What medicine should I give my child?"

    def agent_must_not_run(*args):
        raise AssertionError("AI role called on a clinical question")

    plan = coordinate_visit(
        appointment,
        message,
        readiness_role=agent_must_not_run,
        routing_role=agent_must_not_run,
        resource_role=agent_must_not_run,
        communication_role=agent_must_not_run,
        staff_task_role=lambda review, category: create_mock_staff_task(
            review, category, queue_path=tmp_path / "staff_tasks.json"
        ),
    )
    history_path = tmp_path / "run_history.json"
    record = record_run(plan, "live", history_path=history_path)

    assert [(event.step, event.outcome) for event in record.events] == [
        ("safety_gate", "review"),
        ("readiness", "skipped"),
        ("policy", "review"),
        ("orchestrator", "skipped"),
        ("resource", "skipped"),
        ("communication", "skipped"),
        ("mock_staff_task", "awaiting_confirmation"),
    ]
    submitted = submit_clinical_review(
        plan, confirmed=True,
        staff_task_role=lambda review, category: create_mock_staff_task(
            review, category, queue_path=tmp_path / "staff_tasks.json"
        ),
    )
    submitted_record = record_run(submitted, "live", history_path=history_path)
    assert submitted_record.events[-1].outcome == "queued"
    saved = history_path.read_text(encoding="utf-8")
    assert message not in saved
    assert appointment.patient_name not in saved
    assert "api_key" not in saved.lower()


def test_sample_trace_records_roles_and_appends(tmp_path):
    appointment = get_appointment("DEMO-001", use_saved=False)
    plan = coordinate_visit(
        appointment,
        SAMPLE_CAREGIVER_MESSAGE,
        readiness_role=propose_demo_next_step,
        routing_role=lambda state: (_ for _ in ()).throw(
            AssertionError("Orchestrator should be skipped on human-review cases")
        ),
        resource_role=lambda question, selected_topic: None,
        communication_role=lambda state: (_ for _ in ()).throw(ValueError("Simulated unavailable writer")),
        staff_task_role=lambda review, category: create_mock_staff_task(
            review, category, queue_path=tmp_path / "staff_tasks.json"
        ),
    )
    history_path = tmp_path / "run_history.json"
    first = record_run(plan, "sample", history_path=history_path)
    second = record_run(plan, "sample", history_path=history_path)

    assert first.run_id != second.run_id
    assert [record.run_id for record in list_run_history(history_path=history_path)] == [
        first.run_id,
        second.run_id,
    ]
    outcomes = {event.step: event.outcome for event in first.events}
    assert outcomes["readiness"] == "ran"
    assert outcomes["orchestrator"] == "skipped"
    assert outcomes["resource"] == "skipped"
    assert outcomes["communication"] == "failed"
    assert outcomes["staff_summary_check"] == "review"
    assert outcomes["mock_staff_task"] == "queued"
    saved = history_path.read_text(encoding="utf-8")
    assert SAMPLE_CAREGIVER_MESSAGE not in saved
    assert "Not needed for this sample." not in saved
