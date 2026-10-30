"""Small local trace of coordinated demo runs, without caregiver or model text."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from coordinator import VisitPlan


DEFAULT_HISTORY_PATH = Path(__file__).parent / "runtime" / "run_history.json"
Step = Literal["safety_gate", "readiness", "policy", "orchestrator", "resource", "communication", "staff_summary_check", "mock_staff_task"]
Outcome = Literal["passed", "review", "ran", "skipped", "blocked", "failed", "queued", "not_needed", "awaiting_confirmation"]


class RunEvent(BaseModel):
    step: Step
    outcome: Outcome


class RunRecord(BaseModel):
    run_id: str
    created_at: datetime
    appointment_id: str
    mode: Literal["live", "sample"]
    policy_result: Literal["preview_only", "human_review", "block"]
    events: list[RunEvent]


def build_run_record(plan: VisitPlan, mode: Literal["live", "sample"]) -> RunRecord:
    """Describe observed control flow using fixed labels, never free-form AI text."""
    state = plan.case_state
    if state is None:
        raise ValueError("A coordinated case state is required for run history.")

    pre_model_review = state.pre_model_review_reason is not None
    roles = set(state.completed_roles)
    events = [RunEvent(step="safety_gate", outcome="blocked" if state.pre_model_denial_reason else "review" if pre_model_review else "passed")]
    events.append(RunEvent(step="readiness", outcome="ran" if "readiness" in roles else "skipped"))
    events.append(RunEvent(step="policy", outcome="blocked" if plan.policy_result == "block" else "review" if plan.policy_result == "human_review" else "passed"))
    events.append(RunEvent(step="orchestrator", outcome="ran" if "orchestrator" in roles else "skipped"))
    events.append(RunEvent(step="resource", outcome="ran" if "resource" in roles else "skipped"))
    events.append(RunEvent(step="communication", outcome="ran" if "communication" in roles else "failed" if state.communication_error else "skipped"))
    if state.communication_decision:
        events.append(RunEvent(step="staff_summary_check", outcome="passed" if state.communication_decision.result == "allow_staff_draft" else "review"))
    events.append(RunEvent(step="mock_staff_task", outcome="queued" if state.staff_task else "failed" if state.staff_task_error else "awaiting_confirmation" if state.clinical_gate_triggered else "not_needed"))
    return RunRecord(
        run_id=f"RUN-{uuid4().hex[:8].upper()}",
        created_at=datetime.now(timezone.utc),
        appointment_id=plan.appointment_id,
        mode=mode,
        policy_result=plan.policy_result,
        events=events,
    )


def _history_path() -> Path:
    override = os.getenv("VISITREADY_RUN_HISTORY_PATH", "").strip()
    return Path(override) if override else DEFAULT_HISTORY_PATH


def list_run_history(*, history_path: Path | None = None) -> list[RunRecord]:
    path = history_path or _history_path()
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    return [RunRecord.model_validate(item) for item in records]


def record_run(
    plan: VisitPlan,
    mode: Literal["live", "sample"],
    *,
    history_path: Path | None = None,
) -> RunRecord:
    """Append one completed workflow trace to a local demo file."""
    path = history_path or _history_path()
    record = build_run_record(plan, mode)
    records = list_run_history(history_path=path)
    records.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps([item.model_dump(mode="json") for item in records], indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
    return record
