"""The staff writer receives logistics context only, after the review decision."""

import json
from types import SimpleNamespace

import pytest

from communication_agent import draft_staff_summary
from models import StaffSummaryDraft


def test_staff_writer_receives_minimum_context_and_returns_structured_draft(logistics_review_state, staff_summary_draft):
    captured = {}
    def parse(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_parsed=staff_summary_draft)
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    draft = draft_staff_summary(logistics_review_state, client=client, model="test-model")
    sent = json.loads(captured["input"][1]["content"])
    assert draft == staff_summary_draft
    assert sent["caregiver_message"] == logistics_review_state.caregiver_message
    assert sent["unresolved_items"] == ["transportation", "paperwork"]
    assert "patient_name" not in sent
    assert "appointment" not in sent
    assert "appointment_id" not in sent
    assert "Sofia" not in json.dumps(sent)
    assert captured["text_format"] is StaffSummaryDraft
    assert captured["store"] is False
    assert "tools" not in captured


@pytest.mark.parametrize("route", ["preview", "clinical", "unsupported"])
def test_ineligible_routes_never_reach_the_model(logistics_review_state, route):
    state = logistics_review_state
    if route == "preview":
        state.policy_result = "preview_only"
    elif route == "clinical":
        state.clinical_gate_triggered = True
    else:
        state.pre_model_denial_reason = "out_of_scope"
    with pytest.raises(ValueError, match="eligible logistics"):
        draft_staff_summary(state)


def test_refusal_or_missing_output_raises_for_the_coordinator_to_handle(logistics_review_state):
    client = SimpleNamespace(responses=SimpleNamespace(parse=lambda **kwargs: SimpleNamespace(output_parsed=None)))
    with pytest.raises(ValueError, match="did not return"):
        draft_staff_summary(logistics_review_state, client=client, model="test-model")
