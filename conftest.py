"""Reusable fictional review cases; these fixtures make no API requests."""

import pytest

from models import NextStep, ProposedUpdate, StaffReportedDetail, StaffSummaryDraft
from review import draft_review_request
from tools import get_appointment
from visit_state import VisitReadyState


@pytest.fixture
def logistics_review_state():
    appointment = get_appointment("DEMO-001", use_saved=False)
    message = "My ride fell through. Registration is done. I have the referral, but I don't know if it is the right one."
    proposal = NextStep(
        action="request_human_review",
        reason="A reported ride problem needs staff judgment.",
        message="Staff should review the transportation barrier and paperwork question.",
        proposed_update=ProposedUpdate(
            item="transportation", status="unavailable", evidence="My ride fell through."
        ),
    )
    return VisitReadyState(
        appointment=appointment,
        caregiver_message=message,
        readiness_proposal=proposal,
        review_draft=draft_review_request(appointment, proposal, message),
        policy_result="human_review",
    )


@pytest.fixture
def staff_summary_draft():
    return StaffSummaryDraft(
        summary="The parent reports a lost ride and uncertainty about whether the referral is suitable. Registration is reported complete.",
        reported_details=[
            StaffReportedDetail(item="transportation", statement="The parent reports their ride fell through.", source_quote="My ride fell through."),
            StaffReportedDetail(item="registration", statement="Registration is reported complete.", source_quote="Registration is done."),
            StaffReportedDetail(item="paperwork", statement="The parent is uncertain whether the referral is the right one.", source_quote="I have the referral, but I don't know if it is the right one."),
        ],
        review_items=["transportation", "paperwork"],
    )
