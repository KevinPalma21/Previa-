"""Display-only details for the fictional caregiver demo."""

from pathlib import Path

from pydantic import BaseModel, Field


PROFILE_PATH = Path(__file__).resolve().parent / "data" / "patient_profile.json"


class PatientProfile(BaseModel):
    appointment_id: str
    age_years: int = Field(ge=0, le=120)
    visit_reason: str


def load_patient_profile(appointment_id: str) -> PatientProfile:
    profile = PatientProfile.model_validate_json(PROFILE_PATH.read_text(encoding="utf-8"))
    if profile.appointment_id != appointment_id:
        raise ValueError("The patient display profile does not match this demo visit.")
    return profile
