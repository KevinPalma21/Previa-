"""Local demo queue for fictional logistics and explicitly submitted questions."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from models import ReviewRequest, StaffSummaryDraft


DEFAULT_QUEUE_PATH = Path(__file__).parent / "runtime" / "staff_tasks.json"
TaskCategory = Literal["clinical_question", "visit_logistics", "other_question"]


class MockStaffTask(BaseModel):
    task_id: str
    appointment_id: str
    category: TaskCategory
    status: Literal["awaiting_staff_review", "seen_in_demo"] = "awaiting_staff_review"
    created_at: datetime
    seen_at: datetime | None = None
    staff_summary: StaffSummaryDraft | None = None
    summary_source: Literal["ai_draft", "template"] | None = None
    original_message: str | None = None
    assigned_team: Literal["Appointment care team (demo)", "Care access team (demo)"] | None = None


def _queue_path() -> Path:
    override = os.getenv("VISITREADY_STAFF_QUEUE_PATH", "").strip()
    return Path(override) if override else DEFAULT_QUEUE_PATH


def list_mock_staff_tasks(*, queue_path: Path | None = None) -> list[MockStaffTask]:
    """Read task metadata and any fictional logistics summary."""
    path = queue_path or _queue_path()
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    return [MockStaffTask.model_validate(record) for record in records]


def _write_tasks(tasks: list[MockStaffTask], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps([item.model_dump(mode="json") for item in tasks], indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def create_mock_staff_task(
    review: ReviewRequest,
    category: TaskCategory,
    *,
    queue_path: Path | None = None,
) -> MockStaffTask:
    """Deduplicate identical pending reports; keep distinct logistics reports.

    Only logistics reports carry AI drafts. A clinical question is retained
    verbatim only after the caregiver explicitly requests its demo handoff.
    """
    if review.status != "draft":
        raise ValueError("Only a human-review draft can create a mock staff task.")
    has_summary = review.staff_summary is not None
    if has_summary != (review.summary_source is not None):
        raise ValueError("Staff summary and its source must be supplied together.")
    if has_summary and category != "visit_logistics":
        raise ValueError("Only logistics demo tasks can carry staff summaries.")
    clinical_submission = category == "clinical_question"
    if clinical_submission and not review.caregiver_confirmed:
        raise ValueError("A clinical question requires the caregiver's explicit review request.")
    keep_message = has_summary or clinical_submission
    if keep_message and not 0 < len(review.caregiver_message.strip()) <= 2000:
        raise ValueError("A bounded fictional source report is required.")
    original_message = review.caregiver_message.strip() if keep_message else None
    assigned_team = (
        "Appointment care team (demo)" if clinical_submission else "Care access team (demo)"
    )
    path = queue_path or _queue_path()
    tasks = list_mock_staff_tasks(queue_path=path)
    for task in tasks:
        if (
            task.appointment_id == review.appointment_id
            and task.category == category
            and task.status == "awaiting_staff_review"
        ):
            if task.original_message == original_message and task.assigned_team == assigned_team:
                return task

    task = MockStaffTask(
        task_id=f"VR-{uuid4().hex[:8].upper()}",
        appointment_id=review.appointment_id,
        category=category,
        created_at=datetime.now(timezone.utc),
        staff_summary=review.staff_summary.model_copy(deep=True) if has_summary else None,
        summary_source=review.summary_source,
        original_message=original_message,
        assigned_team=assigned_team,
    )
    tasks.append(task)
    _write_tasks(tasks, path)
    return task


def mark_mock_task_seen(task_id: str, *, queue_path: Path | None = None) -> MockStaffTask:
    """Record that someone clicked a demo button; no clinical review is implied."""
    path = queue_path or _queue_path()
    tasks = list_mock_staff_tasks(queue_path=path)
    for index, task in enumerate(tasks):
        if task.task_id == task_id:
            if task.status == "seen_in_demo":
                return task
            seen = task.model_copy(
                update={"status": "seen_in_demo", "seen_at": datetime.now(timezone.utc)}
            )
            tasks[index] = seen
            _write_tasks(tasks, path)
            return seen
    raise ValueError("Mock staff task not found.")
