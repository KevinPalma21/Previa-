"""The Resource role can retrieve only a topic selected by the Orchestrator."""

import json
from types import SimpleNamespace

import pytest

from resource_agent import find_resource_for_question
from resource_tools import get_public_guidance


@pytest.mark.parametrize(
    "topic,question",
    [
        ("what_to_bring", "What should I bring to the appointment?"),
        ("parking_and_directions", "Where can I find parking information?"),
        ("registration_and_echeckin", "How do I complete MyChart e-check-in?"),
    ],
)
def test_resource_tool_is_restricted_to_selected_topic(topic, question):
    captured = {}
    call = SimpleNamespace(
        type="function_call",
        name="get_public_guidance",
        arguments=json.dumps({"topic": topic}),
    )

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output=[call])

    client = SimpleNamespace(responses=SimpleNamespace(create=create))

    guidance = find_resource_for_question(
        question, topic, client=client, model="test-model"
    )

    assert guidance == get_public_guidance(topic)
    assert captured["tools"][0]["parameters"]["properties"]["topic"]["enum"] == [topic]
    assert captured["store"] is False


def test_resource_role_abstains_when_model_does_not_call_tool():
    client = SimpleNamespace(
        responses=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(output=[])
        )
    )

    result = find_resource_for_question(
        "Can you arrange a ride?",
        "parking_and_directions",
        client=client,
        model="test-model",
    )

    assert result is None


def test_catalog_entries_are_lurie_public_sources():
    for topic in (
        "what_to_bring",
        "parking_and_directions",
        "registration_and_echeckin",
    ):
        guidance = get_public_guidance(topic)
        assert guidance.topic == topic
        assert "luriechildrens.org" in guidance.source_url
