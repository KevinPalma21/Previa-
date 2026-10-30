from pathlib import Path

from models import Appointment
from storage import STATE_PATH, load_appointment


def get_appointment(
    appointment_id: str, *, use_saved: bool = True, state_path: Path = STATE_PATH
) -> Appointment:
    """Read the fictional record and return it only if its ID matches."""
    appointment = load_appointment(use_saved=use_saved, state_path=state_path)

    if appointment.appointment_id != appointment_id:
        raise ValueError("Appointment not found in the sample data.")

    return appointment
