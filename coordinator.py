"""Coordinate bounded model roles and a local staff-review handoff."""

from typing import Callable, Literal

from openai import APIConnectionError, APIError
from pydantic import BaseModel

from communication_agent import draft_staff_summary
from communication_policy import check_staff_summary, make_fallback_staff_summary, staff_summary_allowed
from clinical_gate import pre_model_route
from models import Appointment, NextStep, ReviewRequest, StaffSummaryDraft
from orchestrator_agent import route_resource_lookup
from policies import check_proposal
from readiness_agent import propose_next_step
from resource_agent import find_resource_for_question
from resource_tools import PublicGuidance, ResourceTopic, get_public_guidance
from review import draft_review_request
from staff_tasks import MockStaffTask, TaskCategory, create_mock_staff_task
from visit_state import CommunicationDecision, ResourceRoute, VisitReadyState


class VisitPlan(BaseModel):
    """A preview of findings and proposed next steps, not permission to act."""

    appointment_id: str
    policy_result: Literal["preview_only", "human_review", "block"]
    readiness_proposal: NextStep | None = None
    public_guidance: PublicGuidance | None = None
    review_draft: ReviewRequest | None = None
    case_state: VisitReadyState | None = None


def _plan_from_state(state: VisitReadyState) -> VisitPlan:
    """Expose the case file while keeping the existing app's result shape."""
    if state.policy_result is None:
        raise ValueError("A case cannot become a plan before a policy decision.")
    return VisitPlan(
        appointment_id=state.appointment.appointment_id,
        policy_result=state.policy_result,
        readiness_proposal=state.readiness_proposal,
        public_guidance=state.public_guidance,
        review_draft=state.review_draft,
        case_state=state,
    )


def _queue_review_task(
    state: VisitReadyState,
    category: TaskCategory,
    staff_task_role: Callable[[ReviewRequest, TaskCategory], MockStaffTask],
) -> None:
    """Try the local mock queue without claiming a handoff if it fails."""
    if state.review_draft is None:
        raise ValueError("A review draft is required before making a staff task.")
    try:
        state.staff_task = staff_task_role(state.review_draft, category)
    except (OSError, ValueError) as exc:
        state.staff_task_error = type(exc).__name__


def coordinate_visit(
    appointment: Appointment,
    caregiver_message: str,
    *,
    readiness_role: Callable[[Appointment, str], NextStep] = propose_next_step,
    routing_role: Callable[[VisitReadyState], ResourceRoute] = route_resource_lookup,
    resource_role: Callable[[str, ResourceTopic], PublicGuidance | None] = find_resource_for_question,
    communication_role: Callable[[VisitReadyState], StaffSummaryDraft] = draft_staff_summary,
    staff_task_role: Callable[[ReviewRequest, TaskCategory], MockStaffTask] = create_mock_staff_task,
) -> VisitPlan:
    """Deny unsupported requests, review clinical questions, then check logistics."""
    caregiver_message = caregiver_message.strip()
    if not caregiver_message:
        raise ValueError("Enter a caregiver message before requesting a visit plan.")
    if len(caregiver_message) > 2000:
        raise ValueError("Caregiver message must be 2000 characters or fewer.")

    state = VisitReadyState(
        appointment=appointment.model_copy(deep=True),
        caregiver_message=caregiver_message,
    )
    initial_route = pre_model_route(caregiver_message)
    if initial_route == "denied":
        state.pre_model_denial_reason = "out_of_scope"
        state.policy_result = "block"
        return _plan_from_state(state)
    if initial_route == "clinical_review":
        state.clinical_gate_triggered = True
        state.pre_model_review_reason = "clinical_review"
        state.policy_result = "human_review"
        state.readiness_proposal = NextStep(
            action="request_human_review",
            reason="A clinical or medication question requires qualified staff judgment.",
            message="A staff member should review this question.",
        )
        state.review_draft = ReviewRequest(
            appointment_id=appointment.appointment_id,
            summary="Clinical or medication question requires staff review.",
            caregiver_message=caregiver_message,
            unresolved_items=[],
        )
        # A clinical question is only drafted here. The caregiver's separate
        # review-request action is required before its text enters the queue.
        return _plan_from_state(state)

    proposal = readiness_role(state.appointment.model_copy(deep=True), caregiver_message)
    state.completed_roles.append("readiness")
    decision = check_proposal(proposal, caregiver_message)
    state.policy_result = decision
    if decision == "block":
        return _plan_from_state(state)

    state.readiness_proposal = proposal
    if decision == "human_review":
        state.review_draft = draft_review_request(
            state.appointment, proposal, caregiver_message
        )
        _prepare_staff_summary(state, communication_role)
        _queue_review_task(state, "visit_logistics", staff_task_role)
        return _plan_from_state(state)

    state.resource_route = routing_role(state.model_copy(deep=True))
    state.completed_roles.append("orchestrator")
    if state.resource_route.resource_topic:
        state.public_guidance = resource_role(
            caregiver_message, state.resource_route.resource_topic
        )
        if state.public_guidance and state.resource_route.resource_topic == "parking_and_directions":
            # Bind the approved lookup to trusted visit context in application
            # code. A model cannot invent the scheduled destination or mutate it.
            state.public_guidance = get_public_guidance(
                "parking_and_directions",
                question=caregiver_message,
                appointment_location=state.appointment.location,
            )
        state.completed_roles.append("resource")
    return _plan_from_state(state)


def submit_clinical_review(
    plan: VisitPlan,
    *,
    confirmed: bool,
    staff_task_role: Callable[[ReviewRequest, TaskCategory], MockStaffTask] = create_mock_staff_task,
) -> VisitPlan:
    """Submit an explicitly requested fictional clinical handoff; call no AI."""
    if not confirmed:
        raise ValueError("The caregiver must request the review before submission.")
    state = plan.case_state.model_copy(deep=True) if plan.case_state else None
    if (
        state is None
        or not state.clinical_gate_triggered
        or state.pre_model_review_reason != "clinical_review"
        or state.pre_model_denial_reason is not None
        or plan.policy_result != "human_review"
        or state.policy_result != "human_review"
        or state.review_draft is None
        or state.completed_roles
    ):
        raise ValueError("Only a screened clinical review draft can be submitted here.")
    review = state.review_draft
    if (
        plan.appointment_id != state.appointment.appointment_id
        or review.appointment_id != plan.appointment_id
        or review.caregiver_message != state.caregiver_message
    ):
        raise ValueError("The review must match the screened question and appointment.")
    if state.staff_task is not None:
        return _plan_from_state(state)
    review.caregiver_confirmed = True
    state.staff_task_error = None
    _queue_review_task(state, "clinical_question", staff_task_role)
    return _plan_from_state(state)


def _prepare_staff_summary(
    state: VisitReadyState,
    communication_role: Callable[[VisitReadyState], StaffSummaryDraft],
) -> None:
    """A writing failure never cancels the already-required review task."""
    if state.review_draft is None:
        raise ValueError("A review request is required before staff drafting.")
    if staff_summary_allowed(state):
        try:
            draft = communication_role(state.model_copy(deep=True))
            if not isinstance(draft, StaffSummaryDraft):
                raise ValueError("Communication did not return a staff-summary draft.")
            state.communication_draft = draft
        except (APIError, APIConnectionError, ValueError, TypeError) as exc:
            state.communication_error = type(exc).__name__
            state.communication_decision = CommunicationDecision(
                result="use_fallback", reason="AI drafting was unavailable; use the basic staff summary."
            )
        else:
            state.completed_roles.append("communication")
            state.communication_decision = check_staff_summary(state)
    else:
        state.communication_decision = CommunicationDecision(
            result="use_fallback", reason="This case is not eligible for AI staff-summary drafting."
        )
    if state.communication_decision.result == "allow_staff_draft":
        state.review_draft.staff_summary = state.communication_draft.model_copy(deep=True)
        state.review_draft.summary_source = "ai_draft"
    else:
        state.review_draft.staff_summary = make_fallback_staff_summary(state)
        state.review_draft.summary_source = "template"
