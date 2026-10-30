"""A fixed, clearly simulated proposal for one fictional demo scenario."""

from models import Appointment, NextStep, ProposedUpdate


SAMPLE_CAREGIVER_MESSAGE = "My ride fell through."


def propose_demo_next_step(
    appointment: Appointment, caregiver_message: str
) -> NextStep:
    """Return a prewritten proposal; this function does not call a model."""
    if appointment.appointment_id != "DEMO-001":
        raise ValueError("The sample scenario only supports appointment DEMO-001.")
    if caregiver_message.strip() != SAMPLE_CAREGIVER_MESSAGE:
        raise ValueError("Load the exact sample message to run this scenario.")

    update = None
    if appointment.transportation.status != "unavailable":
        update = ProposedUpdate(
            item="transportation",
            status="unavailable",
            evidence=SAMPLE_CAREGIVER_MESSAGE,
        )

    return NextStep(
        action="request_human_review",
        reason="The caregiver reports that their possible ride fell through.",
        message="Staff should review transportation help for this appointment.",
        proposed_update=update,
    )
