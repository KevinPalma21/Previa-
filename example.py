from readiness import find_unresolved_items
from tools import get_appointment
from policies import check_proposal
from readiness_agent import propose_next_step


appointment = get_appointment("DEMO-001")

print(appointment.model_dump_json(indent=2))

unresolved = find_unresolved_items(appointment)
print("Items needing attention:", unresolved)

print("Asking the live Readiness agent for a proposal...")
proposal = propose_next_step(appointment)

print("Model proposal:")
print(proposal.model_dump_json(indent=2))

decision = check_proposal(proposal)
print("Policy decision:", decision)

if decision == "preview_only":
    print("Local preview only — nothing sent:", proposal.message)
elif decision == "human_review":
    print("Human review required — no request has been sent.")
else:
    print("Proposal blocked: a required explanation or message is missing.")
