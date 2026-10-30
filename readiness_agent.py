import json

from api_client import create_model_client
from models import Appointment, NextStep
from prompts import READINESS_INSTRUCTIONS
from readiness import find_unresolved_items


def propose_next_step(
    appointment: Appointment, caregiver_message: str = "", client=None, model=None
) -> NextStep:
    """Ask the configured model, or a supplied test client, for one proposal."""
    caregiver_message = caregiver_message.strip()
    if len(caregiver_message) > 2000:
        raise ValueError("Caregiver message must be 2000 characters or fewer.")

    if client is None:
        client, configured_model = create_model_client()
        model = model or configured_model
    elif not model:
        raise ValueError("A model name is required when supplying a client.")
    context = {
        "appointment": appointment.model_dump(),
        "unresolved_items": find_unresolved_items(appointment),
        "caregiver_message": caregiver_message,
    }

    response = client.responses.parse(
        model=model,
        reasoning={"effort": "low"},
        store=False,
        input=[
            {"role": "system", "content": READINESS_INSTRUCTIONS},
            {"role": "user", "content": json.dumps(context)},
        ],
        text_format=NextStep,
    )

    if response.output_parsed is None:
        raise ValueError("The model did not return a structured next-step proposal.")

    return response.output_parsed
