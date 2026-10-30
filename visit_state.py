"""The structured case file passed through one VisitReady run."""

from typing import Literal

from pydantic import BaseModel, Field

from models import Appointment, NextStep, ReviewRequest, StaffSummaryDraft
from resource_tools import PublicGuidance, ResourceTopic
from staff_tasks import MockStaffTask


class ResourceRoute(BaseModel):
    """An Orchestrator proposal naming the best approved source, if any."""

    resource_topic: ResourceTopic | None = None
    reason: str


class CommunicationDecision(BaseModel):
    """Whether an internal draft meets the demo's structural/evidence checks."""

    result: Literal["allow_staff_draft", "use_fallback"]
    reason: str


class VisitReadyState(BaseModel):
    """Inputs and accepted findings; this is not a hospital record or audit log."""

    appointment: Appointment
    caregiver_message: str
    completed_roles: list[
        Literal["readiness", "orchestrator", "resource", "communication"]
    ] = Field(default_factory=list)
    readiness_proposal: NextStep | None = None
    resource_route: ResourceRoute | None = None
    public_guidance: PublicGuidance | None = None
    communication_draft: StaffSummaryDraft | None = None
    communication_decision: CommunicationDecision | None = None
    communication_error: str | None = None
    clinical_gate_triggered: bool = False
    pre_model_review_reason: Literal["clinical_review", "other_review"] | None = None
    pre_model_denial_reason: Literal["out_of_scope"] | None = None
    staff_task: MockStaffTask | None = None
    staff_task_error: str | None = None
    policy_result: Literal["preview_only", "human_review", "block"] | None = None
    review_draft: ReviewRequest | None = None
