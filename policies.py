from typing import Literal

from models import NextStep


ALLOWED_STATUSES = {
    "transportation": {"unknown", "unconfirmed", "confirmed", "unavailable"},
    "registration": {"unknown", "incomplete", "confirmed"},
    "paperwork": {"unknown", "unconfirmed", "incomplete", "confirmed"},
}


def check_proposal(
    proposal: NextStep, caregiver_message: str = ""
) -> Literal["preview_only", "human_review", "block"]:
    """Basic routing for a local demo, not medical safety or sending permission."""
    if not proposal.reason.strip():
        return "block"

    if proposal.action != "no_action" and not proposal.message.strip():
        return "block"

    update = proposal.proposed_update
    if update is not None:
        quote = update.evidence.strip()
        if proposal.action == "no_action":
            return "block"
        if update.status not in ALLOWED_STATUSES[update.item]:
            return "block"
        if not quote or quote not in caregiver_message:
            return "block"

    if proposal.action == "request_human_review":
        return "human_review"

    # A reported lost ride is an unresolved access barrier. The model may call
    # it a question, but that label must not suppress the staff-review route.
    if update is not None and update.item == "transportation" and update.status == "unavailable":
        return "human_review"

    return "preview_only"
