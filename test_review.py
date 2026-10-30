"""Regression checks for administrative review drafts."""

from models import NextStep, ProposedUpdate
from review import draft_review_request
from tools import get_appointment


def test_disputed_confirmed_item_is_included_without_changing_record():
    appointment = get_appointment("DEMO-001", use_saved=False)
    message = (
        "The record says registration is confirmed, but I did not complete "
        "registration. I cannot finish it in MyChart."
    )
    proposal = NextStep(
        action="request_human_review",
        reason="The caregiver report conflicts with the saved registration status.",
        message="Staff should review registration.",
        proposed_update=ProposedUpdate(
            item="registration",
            status="incomplete",
            evidence="I did not complete registration.",
        ),
    )

    draft = draft_review_request(appointment, proposal, message)

    assert "registration" in draft.unresolved_items
    assert appointment.registration.status == "confirmed"
