"""Location ambiguity, source grounding, and safety of parking guidance."""

import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from caregiver_response import compose_caregiver_response
from clinical_gate import pre_model_route
from coordinator import VisitPlan, coordinate_visit
from models import NextStep
from parking_tools import load_parking_locations, lookup_parking, map_search_url
from resource_agent import find_resource_for_question
from resource_tools import get_public_guidance
from tools import get_appointment
from visit_state import ResourceRoute


@pytest.mark.parametrize("query,expected", [
    ("Where can I park at the main hospital?", "main_hospital"),
    ("Parking for 225 East Chicago Avenue, Chicago IL 60611", "main_hospital"),
    ("parking 1131 Techny Rd", "northbrook_outpatient"),
    ("Parking at 1121 Techny Road", "northbrook_surgery"),
    ("parking 467 West Deming Place", "lincoln_park"),
    ("parking 3722 W. Touhy Avenue", "skokie_outpatient"),
    ("parking 2301 Enterprise Drive", "westchester_outpatient"),
    ("What's the nearest parking to the main hospital?", "main_hospital"),
    ("Parking at the main hospital for 2 children", "main_hospital"),
    ("I live in Northbrook but my appointment is at 225 E Chicago Ave", "main_hospital"),
])
def test_explicit_destination_matches_without_guessing(query, expected):
    result = lookup_parking(query)
    assert result.status == "matched"
    assert [location.location_id for location in result.locations] == [expected]


@pytest.mark.parametrize("query", ["Where can I park?", "available parking", "Northbrook", "60062", "Skokie"])
def test_uncertain_location_requires_confirmation(query):
    result = lookup_parking(query)
    assert result.status == "choose_location"
    assert result.locations


def test_northbrook_city_does_not_pick_the_wrong_building():
    result = lookup_parking("Where can I park in Northbrook?")
    assert {location.address.split()[0] for location in result.locations} == {"1121", "1131"}


@pytest.mark.parametrize("query", [
    "Parking at main hospital 999 E Chicago Ave",
    "Parking at 11301 West Cermak Road, Westchester",
    "Parking Town and Country in Skokie",
])
def test_unsupported_address_or_different_facility_is_not_substituted(query):
    result = lookup_parking(query)
    assert result.status == "unknown_location"
    assert not result.locations


def test_multiple_explicit_destinations_are_not_silently_collapsed():
    result = lookup_parking("Parking at 1121 Techny or 1131 Techny?")
    assert result.status == "choose_location"
    assert len(result.locations) == 2


@pytest.mark.parametrize("query", ["closest Lurie to me", "I live in 60062, where is parking?", "nearest Lurie near Chicago"])
def test_home_location_does_not_establish_appointment_or_fake_distances(query):
    result = lookup_parking(query)
    assert result.status == "nearby_search"
    assert not result.locations
    assert "cannot calculate" in result.message
    assert "luriechildrens.org" in result.location_finder_url


def test_main_hospital_garages_keep_distinct_addresses_and_sources():
    result = lookup_parking("225 E Chicago Ave")
    main = result.locations[0]
    assert main.address.startswith("225 E.")
    assert [option.address.split()[0] for option in main.options] == ["222", "321"]
    assert "not live space availability" in result.availability_note
    assert "second-floor concierge" in main.options[0].instructions
    for location in load_parking_locations():
        assert urlparse(location.source_url).hostname == "www.luriechildrens.org"
        for option in location.options:
            assert urlparse(option.source_url).hostname == "www.luriechildrens.org"


def test_map_links_include_only_the_public_destination():
    address = "222 E. Huron Street, Chicago, IL 60611"
    parsed = urlparse(map_search_url(address))
    assert parsed.hostname == "www.google.com"
    assert parse_qs(parsed.query) == {"api": ["1"], "query": [address]}


def test_resource_tool_passes_the_location_to_the_grounded_lookup():
    call = SimpleNamespace(type="function_call", name="get_public_guidance",
        arguments=json.dumps({"topic": "parking_and_directions"}))
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output=[call])))
    result = find_resource_for_question("Where can I park at 225 E Chicago Ave?", "parking_and_directions", client=client, model="test-model")
    assert result.parking_help.status == "matched"
    assert result.parking_help.locations[0].location_id == "main_hospital"


def test_coordinated_parking_response_does_not_mark_transportation_confirmed():
    appointment = get_appointment("DEMO-001", use_saved=False)
    before = appointment.model_dump()
    question = "Where can I park at the main hospital?"
    plan = coordinate_visit(
        appointment, question,
        readiness_role=lambda case, text: NextStep(action="ask_question", reason="Public parking request.", message="Which location are you visiting?"),
        routing_role=lambda state: ResourceRoute(resource_topic="parking_and_directions", reason="Parking request."),
        resource_role=lambda text, topic: get_public_guidance(topic, question=text),
        communication_role=lambda state: (_ for _ in ()).throw(AssertionError("Parking must skip Communication")),
    )
    response = compose_caregiver_response(plan)
    assert response.parking_help.status == "matched"
    assert "published parking" in response.next_step
    assert "confirm a ride" not in response.next_step
    assert plan.readiness_proposal.proposed_update is None
    assert plan.case_state.appointment.model_dump() == before
    assert appointment.model_dump() == before
    assert plan.case_state.completed_roles == ["readiness", "orchestrator", "resource"]


def test_review_result_never_displays_parking_cards():
    plan = VisitPlan(appointment_id="DEMO-001", policy_result="human_review",
        readiness_proposal=NextStep(action="request_human_review", reason="Staff needed", message="Review needed"),
        public_guidance=get_public_guidance("parking_and_directions", question="main hospital"))
    assert compose_caregiver_response(plan).parking_help is None


def test_clinical_question_with_parking_still_takes_priority():
    assert pre_model_route("Where can I park, and should I stop my child's medication?") == "clinical_review"
    assert pre_model_route("Where can I park?") == "logistics"


def test_location_query_limit():
    with pytest.raises(ValueError):
        lookup_parking("x" * 2001)
