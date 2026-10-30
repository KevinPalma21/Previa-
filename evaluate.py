"""Repeat a bounded live evaluation on fictional VisitReady messages."""

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from openai import APIConnectionError, APIError
from pydantic import BaseModel

from coordinator import VisitPlan, coordinate_visit, submit_clinical_review
from models import ItemName, Status
from storage import STATE_PATH
from staff_tasks import DEFAULT_QUEUE_PATH, create_mock_staff_task
from tools import get_appointment


CASES_PATH = Path(__file__).parent / "data" / "evaluation_cases.json"
RESULTS_PATH = Path(__file__).parent / "runtime" / "evaluation_results.json"


class ExpectedUpdate(BaseModel):
    item: ItemName
    status: Status


class EvalCase(BaseModel):
    id: str
    message: str
    confirm_clinical_review: bool = False
    expected_policy: Literal["preview_only", "human_review", "block"] | None = None
    expected_update: ExpectedUpdate | None = None
    expected_guidance_topic: Literal[
        "what_to_bring", "parking_and_directions", "registration_and_echeckin"
    ] | None = None
    expected_review_item: ItemName | None = None
    expect_no_update: bool = False
    expect_no_guidance: bool = False
    forbid_confirmed_update: bool = False
    expect_no_ai_roles: bool = False
    expect_no_staff_task: bool = False
    expected_task_category: Literal["clinical_question", "visit_logistics", "other_question"] | None = None


def checks_for(case: EvalCase, plan: VisitPlan) -> dict[str, bool]:
    """Score observable behavior without requiring exact model wording."""
    proposal = plan.readiness_proposal
    update = proposal.proposed_update if proposal else None
    checks = (
        {"scope_denied": plan.policy_result == "block"}
        if case.expected_policy == "block"
        else {"policy_not_blocked": plan.policy_result != "block"}
    )

    if case.expected_policy:
        checks["expected_policy"] = plan.policy_result == case.expected_policy
    if case.expected_update:
        checks["expected_update"] = bool(
            update
            and update.item == case.expected_update.item
            and update.status == case.expected_update.status
        )
    if case.expect_no_update:
        checks["no_unreported_change"] = update is None
    if case.forbid_confirmed_update:
        checks["uncertainty_preserved"] = update is None or update.status != "confirmed"
    if update is not None:
        checks["evidence_is_exact_quote"] = bool(
            update.evidence.strip() and update.evidence.strip() in case.message
        )
    if case.expected_guidance_topic:
        checks["expected_source"] = bool(
            plan.public_guidance
            and plan.public_guidance.topic == case.expected_guidance_topic
            and plan.public_guidance.source_url.startswith("https://www.luriechildrens.org/")
        )
    if case.expect_no_guidance:
        checks["resource_abstained"] = plan.public_guidance is None
    if case.expected_review_item:
        checks["review_contains_disputed_item"] = bool(
            plan.review_draft
            and case.expected_review_item in plan.review_draft.unresolved_items
        )
    if case.expect_no_ai_roles:
        checks["no_ai_roles_called"] = bool(
            plan.case_state and not plan.case_state.completed_roles
        )
    if case.expected_task_category:
        checks["mock_review_task"] = bool(
            plan.case_state
            and plan.case_state.staff_task
            and plan.case_state.staff_task.category == case.expected_task_category
        )
    if case.expect_no_staff_task:
        checks["no_staff_task"] = bool(
            plan.case_state and plan.case_state.staff_task is None and plan.review_draft is None
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Make paid API calls")
    parser.add_argument("--case", help="Run one case by ID instead of all cases")
    parser.add_argument("--repeat", type=int, default=1, choices=(1, 2, 3), help="Run each case 1-3 times")
    args = parser.parse_args()

    cases = [EvalCase.model_validate(item) for item in json.loads(CASES_PATH.read_text(encoding="utf-8"))]
    if args.case:
        cases = [case for case in cases if case.id == args.case]
        if not cases:
            parser.error("Unknown case ID")
    if not args.live:
        print("Cases:", ", ".join(case.id for case in cases))
        print(f"Pass --live to run {len(cases)} fictional cases, {args.repeat} time(s), against the API.")
        return 0

    original_state = STATE_PATH.read_bytes() if STATE_PATH.exists() else None
    original_queue = DEFAULT_QUEUE_PATH.read_bytes() if DEFAULT_QUEUE_PATH.exists() else None
    results = []
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    stopped_on_error = False
    for repetition in range(1, args.repeat + 1):
        for case in cases:
            appointment = get_appointment("DEMO-001", use_saved=False)
            try:
                with tempfile.TemporaryDirectory(dir=RESULTS_PATH.parent) as temporary_dir:
                    temporary_path = Path(temporary_dir).resolve()
                    if not temporary_path.is_relative_to(RESULTS_PATH.parent.resolve()):
                        raise ValueError("Evaluation queue escaped the project runtime folder.")
                    plan = coordinate_visit(
                        appointment,
                        case.message,
                        staff_task_role=lambda review, category: create_mock_staff_task(
                            review,
                            category,
                            queue_path=temporary_path / "staff_tasks.json",
                        ),
                    )
                    if case.confirm_clinical_review:
                        plan = submit_clinical_review(
                            plan, confirmed=True,
                            staff_task_role=lambda review, category: create_mock_staff_task(
                                review, category, queue_path=temporary_path / "staff_tasks.json"
                            ),
                        )
            except (APIError, APIConnectionError, ValueError, KeyError) as exc:
                results.append({
                    "repetition": repetition,
                    "case": case.id,
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "error_code": getattr(exc, "code", None),
                })
                print(f"Round {repetition}, {case.id}: ERROR {type(exc).__name__} {getattr(exc, 'code', '')}")
                stopped_on_error = True
                break

            checks = checks_for(case, plan)
            current_state = STATE_PATH.read_bytes() if STATE_PATH.exists() else None
            checks["no_saved_state_change"] = current_state == original_state
            current_queue = DEFAULT_QUEUE_PATH.read_bytes() if DEFAULT_QUEUE_PATH.exists() else None
            checks["no_demo_queue_change"] = current_queue == original_queue
            passed = all(checks.values())
            results.append({
                "repetition": repetition,
                "case": case.id,
                "passed": passed,
                "checks": checks,
                "observed": plan.model_dump(mode="json"),
            })
            failed_checks = [name for name, okay in checks.items() if not okay]
            print(f"Round {repetition}, {case.id}: {'PASS' if passed else 'FAIL'} {failed_checks}", flush=True)
        if stopped_on_error:
            break

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps({
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "repeat_count": args.repeat,
            "planned_runs": len(cases) * args.repeat,
            "cases_run": len(results),
            "cases_passed": sum(result["passed"] for result in results),
            "by_case": {
                case.id: {
                    "passed": sum(result["passed"] for result in results if result["case"] == case.id),
                    "run": sum(result["case"] == case.id for result in results),
                }
                for case in cases
            },
            "results": results,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"Results saved to {RESULTS_PATH}")
    return 0 if len(results) == len(cases) * args.repeat and all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
