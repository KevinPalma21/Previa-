"""Let a model request one Orchestrator-approved public-guidance lookup."""

import json

from api_client import create_model_client
from resource_tools import PublicGuidance, ResourceTopic, get_public_guidance


def _guidance_tool(selected_topic: ResourceTopic) -> dict:
    """Expose only the one topic selected by the Orchestrator."""
    return {
        "type": "function",
        "name": "get_public_guidance",
        "description": "Retrieve the approved public Lurie Children's guidance for the selected topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "enum": [selected_topic]},
            },
            "required": ["topic"],
            "additionalProperties": False,
        },
        "strict": True,
    }


def find_resource_for_question(
    question: str,
    selected_topic: ResourceTopic,
    *,
    client=None,
    model: str | None = None,
) -> PublicGuidance | None:
    """Use only the Orchestrator-approved tool and return the vetted record."""
    question = question.strip()
    if not question:
        raise ValueError("Enter a question about appointment preparation.")
    if len(question) > 2000:
        raise ValueError("Question must be 2000 characters or fewer.")

    if client is None:
        client, configured_model = create_model_client()
        model = model or configured_model
    elif not model:
        raise ValueError("A model name is required when supplying a client.")

    response = client.responses.create(
        model=model,
        reasoning={"effort": "low"},
        store=False,
        input=[
            {
                "role": "system",
                "content": (
                    "The Orchestrator selected exactly one approved topic for this "
                    "question. Call get_public_guidance only if that topic genuinely "
                    "matches the caregiver's request. Otherwise do not call a tool. "
                    "Never answer from memory or use the lookup to give clinical, "
                    "transportation, or appointment-specific advice."
                ),
            },
            {"role": "user", "content": question},
        ],
        tools=[_guidance_tool(selected_topic)],
        tool_choice="auto",
        parallel_tool_calls=False,
    )

    calls = [item for item in response.output if item.type == "function_call"]
    if not calls:
        return None
    if len(calls) != 1 or calls[0].name != "get_public_guidance":
        raise ValueError("The resource agent requested an unsupported tool action.")

    arguments = json.loads(calls[0].arguments)
    if not isinstance(arguments, dict) or set(arguments) != {"topic"}:
        raise ValueError("The resource agent supplied invalid tool arguments.")
    if arguments["topic"] != selected_topic:
        raise ValueError("The Resource agent requested a topic not selected by the Orchestrator.")
    return get_public_guidance(selected_topic, question=question)
