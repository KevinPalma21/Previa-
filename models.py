from typing import Literal

from pydantic import BaseModel


Status = Literal["unknown", "unconfirmed", "confirmed", "incomplete", "unavailable"]
ItemName = Literal["transportation", "registration", "paperwork"]


class ChecklistItem(BaseModel):
    """What we currently know about one preparation item."""

    status: Status = "unknown"
    evidence: str = ""
    source: str = "not provided"


class AppointmentLocation(BaseModel):
    """The scheduled facility, supplied by appointment data rather than AI."""

    name: str
    address: str
    location_id: str | None = None


class Appointment(BaseModel):
    """A visit and the preparation information that belongs to it."""

    appointment_id: str
    patient_name: str
    location: AppointmentLocation | None = None
    transportation: ChecklistItem
    registration: ChecklistItem
    paperwork: ChecklistItem


class ProposedUpdate(BaseModel):
    """A suggested checklist change with a quote from the latest message."""

    item: ItemName
    status: Status
    evidence: str


class NextStep(BaseModel):
    """A proposed action, not permission to execute it."""

    action: Literal["ask_question", "request_human_review", "no_action"]
    reason: str
    message: str
    proposed_update: ProposedUpdate | None = None


class StaffReportedDetail(BaseModel):
    """A model-written logistics observation with the caregiver's exact words."""

    item: ItemName
    statement: str
    source_quote: str


class StaffSummaryDraft(BaseModel):
    """An internal, unverified staff draft; it never authorizes an action."""

    summary: str
    reported_details: list[StaffReportedDetail]
    review_items: list[ItemName]
    status: Literal["draft"] = "draft"


class ReviewRequest(BaseModel):
    """An unsent administrative review draft for a person to inspect."""

    appointment_id: str
    summary: str
    caregiver_message: str
    unresolved_items: list[ItemName]
    status: Literal["draft"] = "draft"
    staff_summary: StaffSummaryDraft | None = None
    summary_source: Literal["ai_draft", "template"] | None = None
    caregiver_confirmed: bool = False
