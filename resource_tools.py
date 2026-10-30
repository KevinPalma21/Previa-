"""Read a small, verified catalog of public appointment guidance."""

import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from models import AppointmentLocation
from parking_tools import ParkingLookup, lookup_appointment_parking


CATALOG_PATH = Path(__file__).parent / "data" / "public_guidance.json"
ResourceTopic = Literal[
    "what_to_bring",
    "parking_and_directions",
    "registration_and_echeckin",
]


class PublicGuidance(BaseModel):
    topic: ResourceTopic
    summary: str
    source_title: str
    source_url: str
    checked_on: date
    parking_help: ParkingLookup | None = None


def get_public_guidance(
    topic: str, *, question: str = "", appointment_location: AppointmentLocation | None = None
) -> PublicGuidance:
    """Return a known source record; reject topics absent from the catalog."""
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    for record in records:
        guidance = PublicGuidance.model_validate(record)
        if guidance.topic == topic:
            if topic == "parking_and_directions":
                guidance.parking_help = lookup_appointment_parking(question, appointment_location)
                guidance.summary = guidance.parking_help.message
            return guidance
    raise ValueError(f"No verified public guidance for topic: {topic}")
