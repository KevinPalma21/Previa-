"""Exercise the same location follow-up and parking cards a caregiver sees."""

from streamlit.testing.v1 import AppTest

import caregiver_view
from coordinator import VisitPlan, coordinate_visit
from models import NextStep
from resource_tools import get_public_guidance
from visit_state import ResourceRoute


def test_parking_search_changes_destination_without_stale_cards():
    app = AppTest.from_file("app.py").run(timeout=15)
    app.text_input(key="visit_parking_query").set_value("225 E Chicago Ave").run()
    next(button for button in app.button if button.label == "Find parking").click().run()
    assert not app.exception
    text = " ".join(item.value for item in app.markdown)
    assert "222 E. Huron Street" in text
    assert "321 E. Erie Street" in text

    app.text_input(key="visit_parking_query").set_value("Northbrook").run()
    next(button for button in app.button if button.label == "Find parking").click().run()
    assert not app.exception
    assert "Huron-Superior" not in " ".join(item.value for item in app.markdown)
    app.selectbox(key="visit_parking_choice").set_value("northbrook_surgery").run()
    assert not app.exception
    text = " ".join(item.value for item in app.markdown)
    assert "1121 Techny Road" in text
    assert "Surgery Center adjacent lot" in text


def test_chat_parking_lookup_allows_address_followup_without_another_model_call(monkeypatch):
    calls = []
    def fake_coordinate(appointment, question):
        calls.append(question)
        return VisitPlan(
            appointment_id=appointment.appointment_id,
            policy_result="preview_only",
            readiness_proposal=NextStep(action="ask_question", reason="Parking help", message="Which location?"),
            public_guidance=get_public_guidance("parking_and_directions", question=question),
        )
    monkeypatch.setattr(caregiver_view, "coordinate_visit", fake_coordinate)
    monkeypatch.setattr(caregiver_view, "record_run", lambda *args: None)
    app = AppTest.from_file("app.py").run(timeout=15)
    app.text_area(key="caregiver_message").set_value("Where can I park?").run()
    next(button for button in app.button if button.label == "Ask VisitReady").click().run()
    assert not app.exception
    chat_input = next(item for item in app.text_input if item.key.startswith("chat_"))
    chat_input.set_value("225 E Chicago Ave").run()
    next(button for button in app.button if button.label == "Find parking" and "chat_" in button.key).click().run()
    assert not app.exception
    assert calls == ["Where can I park?"]
    assert "222 E. Huron Street" in " ".join(item.value for item in app.markdown)


def test_generic_chat_question_shows_appointment_parking_without_location_input(monkeypatch):
    def controlled_coordinate(appointment, question):
        return coordinate_visit(
            appointment, question,
            readiness_role=lambda case, text: NextStep(action="no_action", reason="General parking request", message=""),
            routing_role=lambda state: ResourceRoute(resource_topic="parking_and_directions", reason="Parking for current appointment"),
            resource_role=lambda text, topic: get_public_guidance(topic, question=text),
            communication_role=lambda state: (_ for _ in ()).throw(AssertionError("Parking must skip Communication")),
        )
    monkeypatch.setattr(caregiver_view, "coordinate_visit", controlled_coordinate)
    monkeypatch.setattr(caregiver_view, "record_run", lambda *args: None)
    app = AppTest.from_file("app.py").run(timeout=15)
    app.text_area(key="caregiver_message").set_value("Where can I find parking?").run()
    next(button for button in app.button if button.label == "Ask VisitReady").click().run()
    assert not app.exception
    text = " ".join(item.value for item in app.markdown)
    assert "Your appointment is at Lurie" in text
    assert "222 E. Huron Street" in text
    assert "321 E. Erie Street" in text
    assert "APPOINTMENT LOCATION" in " ".join(item.value for item in app.caption)
    assert not app.selectbox
