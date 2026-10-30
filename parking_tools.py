"""Match a supplied destination to reviewed public Lurie parking information.

This tool reads a local source catalog. It does not geolocate the family, query
live garage occupancy, or decide where their appointment should take place.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

from pydantic import BaseModel, Field

from models import AppointmentLocation


PARKING_CATALOG_PATH = Path(__file__).parent / "data" / "parking_locations.json"
LOCATION_FINDER_URL = "https://www.luriechildrens.org/en/locations/Search"
AVAILABILITY_NOTE = (
    "These are published parking options, not live space availability. "
    "VisitReady cannot reserve a space. Check the official page for current rates and changes."
)


class ParkingOption(BaseModel):
    name: str
    address: str
    instructions: str
    source_url: str


class ParkingLocation(BaseModel):
    location_id: str
    name: str
    address: str
    aliases: list[str]
    area_terms: list[str]
    source_url: str
    checked_on: date
    options: list[ParkingOption] = Field(min_length=1)


class ParkingLookup(BaseModel):
    status: Literal["matched", "choose_location", "unknown_location", "nearby_search"]
    message: str
    locations: list[ParkingLocation] = Field(default_factory=list)
    availability_note: str = AVAILABILITY_NOTE
    location_finder_url: str = LOCATION_FINDER_URL
    destination_source: Literal["appointment", "caregiver"] | None = None


def map_search_url(address: str) -> str:
    """Send only the public destination address to Maps, never a home address."""
    return "https://www.google.com/maps/search/?" + urlencode({"api": "1", "query": address})


def load_parking_locations() -> list[ParkingLocation]:
    records = json.loads(PARKING_CATALOG_PATH.read_text(encoding="utf-8"))
    return [ParkingLocation.model_validate(record) for record in records]


def _normalize(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    for full, short in (
        ("east", "e"), ("west", "w"), ("north", "n"), ("south", "s"),
        ("avenue", "ave"), ("street", "st"), ("road", "rd"),
        ("drive", "dr"), ("place", "pl"),
    ):
        value = re.sub(rf"\b{full}\b", short, value)
    return value


def _contains(text: str, term: str) -> bool:
    return f" {_normalize(term)} " in f" {text} "


def _matched(locations: list[ParkingLocation]) -> ParkingLookup:
    if len(locations) == 1:
        return ParkingLookup(
            status="matched",
            message=(
                "Of course — here are Lurie's published parking instructions for this location. "
                "Please match the address below to your appointment details."
            ),
            locations=locations,
            destination_source="caregiver",
        )
    return ParkingLookup(
        status="choose_location",
        message="I found more than one possible destination. Which address is on your appointment?",
        locations=locations,
    )


def lookup_appointment_parking(query: str, appointment_location: AppointmentLocation | None) -> ParkingLookup:
    """Use the current visit's destination unless the question needs clarification.

    A location ID alone never overrides a conflicting address. Caregiver wording
    can request another destination, but cannot silently rewrite the appointment.
    """
    question_result = lookup_parking(query)
    if appointment_location is None:
        return question_result

    scheduled = lookup_parking(appointment_location.address)
    named = lookup_parking(appointment_location.name)
    if scheduled.status != "matched" or (
        appointment_location.location_id
        and scheduled.locations[0].location_id != appointment_location.location_id
    ) or (
        named.status == "matched"
        and named.locations[0].location_id != scheduled.locations[0].location_id
    ):
        return ParkingLookup(
            status="unknown_location",
            message=(
                f"Your appointment lists {appointment_location.name} at {appointment_location.address}, "
                "but I couldn't verify that destination against my reviewed parking information. "
                "Please confirm the appointment address before choosing parking."
            ),
        )

    location = scheduled.locations[0]
    if question_result.status == "nearby_search" and re.search(r"\bpark(?:ing)?\b", _normalize(query)) and not re.search(r"\b(?:i live|my home|home address|closest lurie|nearest lurie)\b", _normalize(query)):
        # "Where is nearby parking?" means parking for the current visit.
        # This lists published options; it does not claim to rank their distance.
        question_result = lookup_parking("")
    if question_result.status in {"unknown_location", "nearby_search"}:
        return question_result
    if question_result.status == "matched":
        mentioned = question_result.locations
    elif question_result.locations and len(question_result.locations) < len(load_parking_locations()):
        mentioned = question_result.locations
    else:
        mentioned = []

    # An explicit but unsupported destination must not default to the appointment.
    # A generic "parking for my appointment" still uses the scheduled location.
    explicit = re.search(r"\b(?:park(?:ing)? (?:at|in)|going to|visiting)\s+(.+)", _normalize(query))
    if not mentioned and explicit and not re.match(r"(?:my|our|the|this) (?:appointment|visit|hospital)\b", explicit.group(1)):
        return ParkingLookup(
            status="unknown_location",
            message=(
                f"Your appointment lists {location.name} at {location.address}. "
                "I couldn't verify the other location in your question. Which destination do you need parking for?"
            ),
        )

    different = [item for item in mentioned if item.location_id != location.location_id]
    if different:
        return ParkingLookup(
            status="choose_location",
            message=(
                f"Your appointment lists {location.name} at {location.address}, "
                "but your question mentions another possible location. Which address do you need parking for? "
                "Choosing parking here will not change your appointment."
            ),
            locations=[location, *different],
        )

    return ParkingLookup(
        status="matched",
        message=(
            f"Your appointment is at {location.name}, {location.address}. "
            "Here are Lurie's published parking options for that location."
        ),
        locations=[location],
        destination_source="appointment",
    )


def lookup_parking(query: str) -> ParkingLookup:
    """Require a specific destination; retain uncertainty rather than guess."""
    if len(query) > 2000:
        raise ValueError("Location search must be 2000 characters or fewer.")
    text = _normalize(query)
    locations = load_parking_locations()

    # If a family mentions home and a scheduled destination, use the latter.
    destination = re.search(r"\b(?:appointment (?:is )?at|going to|visiting)\s+(.+)", text)
    if destination:
        text = destination.group(1)
    precise = [location for location in locations if any(_contains(text, alias) for alias in location.aliases)]

    # A home city/ZIP does not establish an appointment destination. Use the
    # hospital's location finder for proximity; this catalog has no distances.
    if (not precise or re.search(r"\b(?:i live|my home|home address)\b", text)) and re.search(r"\b(?:closest|nearest|near me|nearby|i live|my home|home address)\b", text):
        return ParkingLookup(
            status="nearby_search",
            message=(
                "If you already have an appointment, use its location even if another clinic is closer. "
                "Otherwise, open Lurie's location finder and enter your city or ZIP, or use Near Me. "
                "Then share the chosen facility's address here for parking help. "
                "This demo cannot calculate the closest facility."
            ),
        )

    # These are different facilities from the centers included in this demo.
    if any(_contains(text, term) for term in ("town and country", "town country", "westbrook", "cermak")):
        return ParkingLookup(
            status="unknown_location",
            message="That facility is not in my reviewed parking catalog. Please check Lurie's location finder for its official parking page.",
        )

    # A mismatching street number must never fall back to a city/name match.
    street_numbers = set(re.findall(
        r"\b(\d{1,5})\s+(?:[nesw]\s+)?(?:[a-z]+\s+){0,3}(?:st|ave|rd|dr|pl|blvd)\b", text
    ))
    street_numbers.update(re.findall(
        r"\b(\d{1,5})\s+(?:[nesw]\s+)?(?:chicago|techny|clark|deming|touhy|enterprise|cermak|huron|erie)\b", text
    ))
    if street_numbers:
        precise = [
            location for location in precise
            if street_numbers & set(re.findall(r"\b\d{1,4}\b", location.address))
        ]
        if not precise:
            return ParkingLookup(
                status="unknown_location",
                message="I couldn't verify that address in my reviewed parking catalog. Please double-check the appointment address or use Lurie's location finder.",
            )
    if precise:
        return _matched(precise)

    candidates = [location for location in locations if any(_contains(text, term) for term in location.area_terms)]
    if candidates:
        return ParkingLookup(
            status="choose_location",
            message="Please confirm the facility and address on your appointment before I show its parking instructions.",
            locations=candidates,
        )
    return ParkingLookup(
        status="choose_location",
        message=(
            "Of course — which Lurie Children's location are you visiting? "
            "Enter the facility name or address from your appointment, or choose a reviewed location below."
        ),
        locations=locations,
    )
