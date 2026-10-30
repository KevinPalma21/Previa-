"""Quote and scope checks bound drafts but do not certify every interpretation."""

import pytest

from communication_policy import check_staff_summary, make_fallback_staff_summary


def test_evidence_linked_staff_draft_is_eligible_for_human_verification(logistics_review_state, staff_summary_draft):
    logistics_review_state.communication_draft = staff_summary_draft
    decision = check_staff_summary(logistics_review_state)
    assert decision.result == "allow_staff_draft"
    assert "staff must verify" in decision.reason


@pytest.mark.parametrize("bad_summary", [
    "A ride has been booked.",
    "Staff have been contacted.",
    "The appointment is scheduled for 2035.",
    "Stop your child's medication.",
    "Visit https://example.com",
    "<img src='private'>",
])
def test_unsupported_claims_or_links_use_fallback(logistics_review_state, staff_summary_draft, bad_summary):
    staff_summary_draft.summary = bad_summary
    logistics_review_state.communication_draft = staff_summary_draft
    assert check_staff_summary(logistics_review_state).result == "use_fallback"


def test_fabricated_quote_cannot_reach_the_staff_task(logistics_review_state, staff_summary_draft):
    staff_summary_draft.reported_details[0].source_quote = "A taxi is guaranteed."
    logistics_review_state.communication_draft = staff_summary_draft
    assert check_staff_summary(logistics_review_state).result == "use_fallback"


def test_missing_primary_barrier_and_extra_review_items_use_fallback(logistics_review_state, staff_summary_draft):
    logistics_review_state.communication_draft = staff_summary_draft
    staff_summary_draft.review_items = ["paperwork"]
    assert check_staff_summary(logistics_review_state).result == "use_fallback"
    staff_summary_draft.review_items = ["transportation", "registration"]
    assert check_staff_summary(logistics_review_state).result == "use_fallback"


def test_fallback_uses_checked_quote_and_never_model_prose(logistics_review_state):
    logistics_review_state.readiness_proposal.message = "Invented unsafe model prose"
    fallback = make_fallback_staff_summary(logistics_review_state)
    assert "Invented" not in fallback.summary
    assert fallback.reported_details[0].source_quote == "My ride fell through."
    assert fallback.review_items == ["transportation"]
