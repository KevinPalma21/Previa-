"""Build a local human-review draft from a policy-checked proposal."""

from models import Appointment, NextStep, ReviewRequest
from policies import check_proposal
from readiness import find_unresolved_items


def draft_review_request(
    appointment: Appointment, proposal: NextStep, caregiver_message: str
) -> ReviewRequest:
    """Return an unsent draft only when the proposal calls for human review."""
    if check_proposal(proposal, caregiver_message) != "human_review":
        raise ValueError("This proposal does not qualify for human review.")

    unresolved_items = find_unresolved_items(appointment)
    update = proposal.proposed_update
    if update is not None and update.item not in unresolved_items:
        unresolved_items.append(update.item)

    return ReviewRequest(
        appointment_id=appointment.appointment_id,
        summary=proposal.message.strip(),
        caregiver_message=caregiver_message.strip(),
        unresolved_items=unresolved_items,
    )
