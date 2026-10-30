"""Apply a caregiver-approved checklist report to an in-memory copy."""

from models import Appointment, ChecklistItem, NextStep
from policies import check_proposal


def apply_approved_update(
    appointment: Appointment,
    proposal: NextStep,
    caregiver_message: str,
    *,
    approved: bool = False,
) -> Appointment:
    """Return an updated copy; never change the original appointment."""
    if not approved:
        raise PermissionError("Caregiver approval is required.")

    update = proposal.proposed_update
    if update is None:
        raise ValueError("This proposal contains no checklist update.")
    if check_proposal(proposal, caregiver_message) == "block":
        raise ValueError("The proposed update failed the policy check.")

    revised = appointment.model_copy(deep=True)
    setattr(
        revised,
        update.item,
        ChecklistItem(
            status=update.status,
            evidence=update.evidence.strip(),
            source="caregiver report",
        ),
    )
    return revised
