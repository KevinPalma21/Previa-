"""Read fictional appointment state and save approved local changes."""

from pathlib import Path

from models import Appointment, NextStep
from updates import apply_approved_update


ROOT = Path(__file__).parent
SEED_PATH = ROOT / "data" / "appointment.json"
STATE_PATH = ROOT / "runtime" / "appointment.json"


def load_appointment(*, use_saved: bool = True, state_path: Path = STATE_PATH) -> Appointment:
    """Keep reported checklist changes; read the destination from visit data.

    Older saved demo records may predate the location field. The seed represents
    the appointment feed here, so local checklist storage must not override its
    scheduled location or carry a stale destination after the visit changes.
    """
    scheduled = Appointment.model_validate_json(SEED_PATH.read_text(encoding="utf-8"))
    if not use_saved or not state_path.exists():
        return scheduled
    saved = Appointment.model_validate_json(state_path.read_text(encoding="utf-8"))
    if saved.appointment_id != scheduled.appointment_id:
        raise ValueError("Saved preparation state belongs to a different appointment.")
    saved.location = scheduled.location.model_copy(deep=True) if scheduled.location else None
    return saved


def _write_appointment(appointment: Appointment, *, state_path: Path) -> None:
    """Persist one validated fictional appointment without changing the seed."""
    original = Appointment.model_validate_json(SEED_PATH.read_text(encoding="utf-8"))
    if appointment.appointment_id != original.appointment_id:
        raise ValueError("Only the sample appointment can be saved in this demo.")

    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = state_path.with_suffix(".tmp")
    temporary_path.write_text(appointment.model_dump_json(indent=2), encoding="utf-8")
    temporary_path.replace(state_path)


def save_approved_update(
    appointment: Appointment,
    proposal: NextStep,
    caregiver_message: str,
    *,
    approved: bool = False,
    state_path: Path = STATE_PATH,
) -> Appointment:
    """Apply policy and approval checks before saving the revised appointment."""
    revised = apply_approved_update(
        appointment, proposal, caregiver_message, approved=approved
    )
    _write_appointment(revised, state_path=state_path)
    return revised
