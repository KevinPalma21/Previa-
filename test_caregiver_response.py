"""Check the caregiver wording at the safety and source boundaries."""

from caregiver_response import compose_caregiver_response
from coordinator import VisitPlan
from models import NextStep, ProposedUpdate
from resource_tools import get_public_guidance


def test_human_review_never_claims_staff_were_contacted():
    plan = VisitPlan(
        appointment_id="DEMO-001",
        policy_result="human_review",
        readiness_proposal=NextStep(
            action="request_human_review",
            reason="A caregiver reports a ride problem.",
            message="Staff should review the ride issue.",
        ),
    )

    response = compose_caregiver_response(plan)

    assert response.staff_review_needed
    assert "nothing has been sent" in response.next_step
    assert "Staff should review" not in response.next_step


def test_public_guidance_keeps_its_source():
    guidance = get_public_guidance("what_to_bring")
    plan = VisitPlan(
        appointment_id="DEMO-001",
        policy_result="preview_only",
        readiness_proposal=NextStep(
            action="ask_question",
            reason="The ride status is unclear.",
                message="Have you been able to confirm a ride for the appointment?",
        ),
        public_guidance=guidance,
    )

    response = compose_caregiver_response(plan)

    assert response.next_step == "Have you been able to confirm a ride for the appointment?"
    assert response.public_guidance == guidance.summary
    assert response.source_url == guidance.source_url


def test_blocked_plan_does_not_show_agent_or_resource_content():
    plan = VisitPlan(appointment_id="DEMO-001", policy_result="block")

    response = compose_caregiver_response(plan)

    assert "could not safely prepare" in response.next_step
    assert response.public_guidance is None
    assert not response.staff_review_needed


def test_untrusted_readiness_wording_never_becomes_caregiver_text():
    unsafe_wording = "Stop your child's medicine before the visit."
    plan = VisitPlan(
        appointment_id="DEMO-001",
        policy_result="preview_only",
        readiness_proposal=NextStep(
            action="ask_question",
            reason="The model made a bad proposal.",
            message=unsafe_wording,
        ),
    )

    response = compose_caregiver_response(plan)

    assert unsafe_wording not in response.next_step
    assert "contact your care team" in response.next_step


def test_quote_supported_checklist_item_selects_a_fixed_question():
    plan = VisitPlan(
        appointment_id="DEMO-001",
        policy_result="preview_only",
        readiness_proposal=NextStep(
            action="ask_question",
            reason="Caregiver reports a lost ride.",
            message="Find me a new ride immediately.",
            proposed_update=ProposedUpdate(
                item="transportation",
                status="unavailable",
                evidence="My ride fell through.",
            ),
        ),
    )

    response = compose_caregiver_response(plan)

    assert response.next_step == "Have you been able to confirm a ride for the appointment?"
    assert "Find me a new ride" not in response.next_step
