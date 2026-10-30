"""Parking uses the current appointment record, not a model's guessed location."""

import json

import pytest

from caregiver_response import compose_caregiver_response
from coordinator import coordinate_visit
from models import AppointmentLocation, NextStep
from parking_tools import lookup_appointment_parking
from resource_tools import get_public_guidance
from storage import load_appointment
from tools import get_appointment
from visit_state import ResourceRoute


@pytest.mark.parametrize("question", [
    "Where can I park?", "Where can I find parking?", "Is parking available?",
    "Where is nearby parking?", "Parking for my appointment?",
])
def test_generic_parking_question_uses_appointment_without_reasking(question):
    appointment = get_appointment("DEMO-001", use_saved=False)
    result = lookup_appointment_parking(question, appointment.location)
    assert result.status == "matched"
    assert result.destination_source == "appointment"
    assert result.locations[0].location_id == "main_hospital"
    assert "Your appointment is at" in result.message
    assert "which" not in result.message.lower()
    assert [option.address.split()[0] for option in result.locations[0].options] == ["222", "321"]


def test_missing_appointment_location_still_asks():
    result = lookup_appointment_parking("Where can I park?", None)
    assert result.status == "choose_location"
    assert result.destination_source is None


def test_explicit_conflicting_destination_requires_confirmation():
    appointment = get_appointment("DEMO-001", use_saved=False)
    before = appointment.model_dump()
    result = lookup_appointment_parking("Where can I park at 1131 Techny Road?", appointment.location)
    assert result.status == "choose_location"
    assert {location.location_id for location in result.locations} == {"main_hospital", "northbrook_outpatient"}
    assert "will not change your appointment" in result.message
    assert appointment.model_dump() == before


@pytest.mark.parametrize("name,address,location_id", [
    ("Lurie main hospital", "999 Unverified Road", "main_hospital"),
    ("Lurie main hospital", "3722 W Touhy Avenue, Skokie", "main_hospital"),
    ("Lurie main hospital", "3722 W Touhy Avenue, Skokie", None),
])
def test_inconsistent_or_unmapped_record_does_not_guess(name, address, location_id):
    record = AppointmentLocation(name=name, address=address, location_id=location_id)
    result = lookup_appointment_parking("Where can I park?", record)
    assert result.status == "unknown_location"
    assert not result.locations


def test_unsupported_explicit_question_does_not_silently_use_default_hospital():
    record = get_appointment("DEMO-001", use_saved=False).location
    result = lookup_appointment_parking("Where can I park in Glenview?", record)
    assert result.status == "unknown_location"
    assert "couldn't verify the other location" in result.message


def test_changing_appointment_changes_generic_parking_answer():
    northbrook = AppointmentLocation(name="Outpatient Center in Northbrook", address="1131 Techny Road, Northbrook, IL 60062", location_id="northbrook_outpatient")
    result = lookup_appointment_parking("Where can I find parking?", northbrook)
    assert result.status == "matched"
    assert result.locations[0].location_id == "northbrook_outpatient"
    assert "Huron" not in result.model_dump_json()


@pytest.mark.parametrize("old_location", [None, {"name": "Old location", "address": "1131 Techny Road", "location_id": "northbrook_outpatient"}])
def test_saved_checklist_uses_scheduled_location_and_keeps_reported_changes(tmp_path, old_location):
    original = get_appointment("DEMO-001", use_saved=False)
    saved = original.model_dump()
    if old_location is None:
        saved.pop("location")
    else:
        saved["location"] = old_location
    saved["paperwork"]["status"] = "incomplete"
    path = tmp_path / "old_appointment.json"
    path.write_text(json.dumps(saved), encoding="utf-8")
    loaded = load_appointment(state_path=path)
    assert loaded.location == original.location
    assert loaded.paperwork.status == "incomplete"
    # Loading migrates context in memory; it does not rewrite the saved record.
    assert json.loads(path.read_text(encoding="utf-8")) == saved


def test_coordinator_binds_tool_result_to_current_appointment_context():
    appointment = get_appointment("DEMO-001", use_saved=False)
    before = appointment.model_dump()
    plan = coordinate_visit(
        appointment, "Where can I find parking?",
        readiness_role=lambda case, text: NextStep(action="no_action", reason="Public parking lookup; no checklist update.", message=""),
        routing_role=lambda state: ResourceRoute(resource_topic="parking_and_directions", reason="Parking request for the recorded destination."),
        resource_role=lambda question, topic: get_public_guidance(topic, question=question),
        communication_role=lambda state: (_ for _ in ()).throw(AssertionError("Parking must skip Communication")),
    )
    response = compose_caregiver_response(plan)
    assert response.parking_help.destination_source == "appointment"
    assert response.parking_help.locations[0].location_id == "main_hospital"
    assert "Your appointment is at" in response.next_step
    assert plan.readiness_proposal.proposed_update is None
    assert appointment.model_dump() == before
    assert plan.case_state.appointment.model_dump() == before
