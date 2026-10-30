"""Turn a checked visit plan into a clear, limited caregiver response."""

from pydantic import BaseModel

from coordinator import VisitPlan
from readiness import find_unresolved_items
from safe_questions import QUESTIONS_BY_ITEM
from parking_tools import ParkingLookup


class CaregiverResponse(BaseModel):
    """Display text only; creating this object does not change or send anything."""

    next_step: str
    public_guidance: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    staff_review_needed: bool = False
    mock_staff_task_id: str | None = None
    parking_help: ParkingLookup | None = None


def _safe_readiness_question(plan: VisitPlan) -> str:
    """Select fixed logistics wording without displaying model-generated prose."""
    proposal = plan.readiness_proposal
    if proposal is None:
        raise ValueError("A readiness proposal is required to choose a question.")

    if proposal.proposed_update:
        return QUESTIONS_BY_ITEM[proposal.proposed_update.item]

    unresolved = (
        find_unresolved_items(plan.case_state.appointment)
        if plan.case_state
        else []
    )
    for item, question in QUESTIONS_BY_ITEM.items():
        if proposal.message.strip() == question and (not plan.case_state or item in unresolved):
            return question

    if len(unresolved) == 1:
        return QUESTIONS_BY_ITEM[unresolved[0]]

    return (
        "I can help with transportation, registration, or paperwork. Which would you "
        "like help with? For medical questions, please contact your care team for guidance."
    )


def compose_caregiver_response(plan: VisitPlan) -> CaregiverResponse:
    """Use the approved plan fields, with fixed wording for sensitive states."""
    if plan.case_state and plan.case_state.pre_model_denial_reason:
        return CaregiverResponse(
            next_step="I'm sorry, I can't help with that topic here."
        )
    proposal = plan.readiness_proposal
    if plan.policy_result == "block" or proposal is None:
        return CaregiverResponse(
            next_step=(
                "I'm sorry, I could not safely prepare a helpful response. Please contact "
                "your care team directly so they can help."
            )
        )

    if plan.policy_result == "human_review" or proposal.action == "request_human_review":
        clinical = bool(plan.case_state and plan.case_state.clinical_gate_triggered)
        task = plan.case_state.staff_task if plan.case_state else None
        if clinical:
            if task:
                next_step = (
                    "Your question is awaiting care team review."
                )
            elif plan.case_state.staff_task_error:
                next_step = (
                    "I'm sorry, I couldn't add your question to the review queue. "
                    "Nothing has been submitted. You can try requesting the review again."
                )
            else:
                next_step = (
                    "I can't advise on medicines or other clinical decisions. "
                    "This question needs care team review."
                )
        elif task:
            next_step = (
                "I'm sorry you're dealing with this. Your concern is in the care-team "
                "review queue for a person to review."
            )
        else:
            next_step = (
                "I'm sorry this is adding stress. A review note is ready for a person to look "
                "at, but nothing has been sent. Please contact your care "
                "team for help with next steps."
            )
        needs_review = True
    elif proposal.action == "ask_question":
        next_step = _safe_readiness_question(plan)
        needs_review = False
    else:
        next_step = (
            "Thanks for sharing that. I don't see a new checklist step to update. If you "
            "still have a concern, your care team can help."
        )
        needs_review = False

    guidance = plan.public_guidance
    # A parking lookup must not imply that a ride or checklist item is resolved.
    # Review and blocked states keep their safety wording and hide parking data.
    parking_help = guidance.parking_help if guidance and not needs_review else None
    if parking_help:
        next_step = parking_help.message
    return CaregiverResponse(
        next_step=next_step,
        public_guidance=guidance.summary if guidance else None,
        source_title=guidance.source_title if guidance else None,
        source_url=guidance.source_url if guidance else None,
        staff_review_needed=needs_review,
        parking_help=parking_help,
        mock_staff_task_id=(
            plan.case_state.staff_task.task_id
            if plan.case_state and plan.case_state.staff_task
            else None
        ),
    )
