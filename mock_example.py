"""Exercise the same agent pipeline with a fake model response; no API call."""
import json
from pathlib import Path
from types import SimpleNamespace

from models import NextStep, ProposedUpdate
from policies import check_proposal
from readiness_agent import propose_next_step
from review import draft_review_request
from tools import get_appointment
from storage import save_approved_update


appointment = get_appointment("DEMO-001", use_saved=False)

# Pretend the model returned this answer, so we can test the connection locally.
fake_response = SimpleNamespace(
    output_parsed=NextStep(
        action="request_human_review",
        reason="The caregiver now reports that the possible ride fell through.",
        message="The caregiver needs help with transportation arrangements.",
        proposed_update=ProposedUpdate(
            item="transportation",
            status="unavailable",
            evidence="My ride fell through.",
        ),
    )
)

# The fake client records the requested structured-output type and returns our sample.
def pretend_parse(**request):
    print("Request used model:", request["model"])
    print("Requested response structure:", request["text_format"].__name__)
    context = json.loads(request["input"][1]["content"])
    print("Caregiver message passed to the agent:", context["caregiver_message"])
    return fake_response


fake_client = SimpleNamespace(
    responses=SimpleNamespace(parse=pretend_parse)
)

proposal = propose_next_step(
    appointment,
    caregiver_message="My ride fell through.",
    client=fake_client,
    model="mock-model",
)
print("Proposal:", proposal.model_dump())
print("Policy decision:", check_proposal(proposal, "My ride fell through."))
print("Original transportation status:", appointment.transportation.status)

# Use a separate demo state file so the starter and normal runtime stay untouched.
demo_state_path = Path(__file__).parent / "runtime" / "mock_appointment.json"
try:
    save_approved_update(
        appointment, proposal, "My ride fell through.", state_path=demo_state_path
    )
except PermissionError:
    print("Without caregiver approval: update refused")

revised = save_approved_update(
    appointment, proposal, "My ride fell through.",
    approved=True, state_path=demo_state_path
)
print("Approved copy's transportation status:", revised.transportation.status)
print("Approved copy's source:", revised.transportation.source)
print("Original remains:", appointment.transportation.status)

reloaded = get_appointment("DEMO-001", state_path=demo_state_path)
print("Reloaded transportation status:", reloaded.transportation.status)
review_draft = draft_review_request(reloaded, proposal, "My ride fell through.")
print("Human-review draft:", review_draft.model_dump())
print("This is a mock response, not an AI-generated answer.")
