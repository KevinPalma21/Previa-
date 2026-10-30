"""The routing model receives only what it needs to select an approved source."""

import json
from types import SimpleNamespace

from models import NextStep
from orchestrator_agent import route_resource_lookup
from tools import get_appointment
from visit_state import ResourceRoute, VisitReadyState


def test_route_uses_structured_output_and_omits_patient_details():
    captured = {}

    def parse(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            output_parsed=ResourceRoute(
                resource_topic="what_to_bring",
                reason="The caregiver asks what to bring.",
            )
        )

    state = VisitReadyState(
        appointment=get_appointment("DEMO-001", use_saved=False),
        caregiver_message="What should I bring?",
        readiness_proposal=NextStep(
            action="ask_question",
            reason="Paperwork is unknown.",
            message="Is your paperwork complete?",
        ),
        policy_result="preview_only",
    )
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))

    route = route_resource_lookup(state, client=client, model="test-model")

    sent = json.loads(captured["input"][1]["content"])
    assert route.resource_topic == "what_to_bring"
    assert sent["caregiver_message"] == "What should I bring?"
    assert set(sent["available_resource_topics"]) == {
        "what_to_bring", "parking_and_directions", "registration_and_echeckin"
    }
    assert "patient_name" not in sent
    assert "appointment" not in sent
    assert sent["appointment_location"] == state.appointment.location.model_dump()
    assert "Sofia" not in json.dumps(sent)
    assert captured["text_format"] is ResourceRoute
    assert captured["store"] is False
