"""Bound staff drafts by route, length, quoted evidence, and logistics scope.

These checks do not prove that every paraphrase is faithful. The staff UI marks
AI content as an unverified draft and shows the original fictional report.
"""

import re

from clinical_gate import needs_clinical_review
from models import StaffReportedDetail, StaffSummaryDraft
from visit_state import CommunicationDecision, VisitReadyState


_UNSUPPORTED_ACTION = re.compile(
    r"\b(?:booked|reserved|arranged|scheduled|approved|guaranteed|resolved|"
    r"staff (?:has|have) been contacted|message (?:has been |was )?sent|"
    r"no (?:staff|human) review (?:is )?(?:needed|required)|"
    r"(?:must|should) (?:take|give|stop|start)|"
    r"(?:high|low|urgent|emergency) priority|immediately)\b", re.IGNORECASE,
)


def staff_summary_allowed(state: VisitReadyState) -> bool:
    """Known clinical/out-of-scope routes never call this AI role."""
    return bool(
        state.policy_result == "human_review"
        and state.readiness_proposal is not None
        and state.review_draft is not None
        and state.pre_model_review_reason is None
        and state.pre_model_denial_reason is None
        and not state.clinical_gate_triggered
        and not needs_clinical_review(state.caregiver_message)
        and not needs_clinical_review(state.readiness_proposal.reason)
        and not needs_clinical_review(state.readiness_proposal.message)
    )


def check_staff_summary(state: VisitReadyState) -> CommunicationDecision:
    """Allow a draft for STAFF verification; never approve a clinical action."""
    def fallback(reason: str) -> CommunicationDecision:
        return CommunicationDecision(result="use_fallback", reason=reason)

    draft = state.communication_draft
    if not staff_summary_allowed(state) or not isinstance(draft, StaffSummaryDraft):
        return fallback("No eligible logistics staff draft is available.")
    if not draft.summary.strip() or len(draft.summary) > 600:
        return fallback("Staff summary is missing or too long.")
    if not 1 <= len(draft.reported_details) <= 6:
        return fallback("A staff draft needs one to six evidence-linked details.")
    allowed_items = set(state.review_draft.unresolved_items)
    if not draft.review_items or not set(draft.review_items) <= allowed_items:
        return fallback("The draft requests review beyond the checked unresolved items.")
    if len(draft.review_items) != len(set(draft.review_items)):
        return fallback("The draft repeats a review item.")
    update = state.readiness_proposal.proposed_update
    if update and update.item not in draft.review_items:
        return fallback("The reported change requiring review was omitted.")

    seen = set()
    for detail in draft.reported_details:
        quote = detail.source_quote.strip()
        if not quote or quote not in state.caregiver_message:
            return fallback("A reported detail lacks an exact quote from the current message.")
        if not detail.statement.strip() or len(detail.statement) > 240:
            return fallback("A reported detail is missing or too long.")
        if (detail.item, quote) in seen:
            return fallback("The draft repeats a reported detail.")
        seen.add((detail.item, quote))

    wording = " ".join([draft.summary, *[detail.statement for detail in draft.reported_details]])
    if needs_clinical_review(wording) or _UNSUPPORTED_ACTION.search(wording):
        return fallback("Draft wording goes beyond the supported staff-summary scope.")
    if re.search(r"https?://|www\.|!\[|<[^>]+>", wording, re.IGNORECASE):
        return fallback("Staff drafts cannot introduce links or markup.")
    if not set(re.findall(r"\d+", wording)) <= set(re.findall(r"\d+", state.caregiver_message)):
        return fallback("Draft wording includes numbers absent from the current report.")
    return CommunicationDecision(
        result="allow_staff_draft",
        reason="Draft meets structure, quote and scope checks; staff must verify its meaning.",
    )


def make_fallback_staff_summary(state: VisitReadyState) -> StaffSummaryDraft:
    """Keep the review task usable when AI writing fails or fails its checks."""
    if state.review_draft is None or state.readiness_proposal is None:
        raise ValueError("A checked review request is required.")
    update = state.readiness_proposal.proposed_update
    details = []
    if update and update.evidence.strip() and update.evidence.strip() in state.caregiver_message:
        details.append(StaffReportedDetail(
            item=update.item,
            statement=f"Parent or guardian reports {update.item} as {update.status}.",
            source_quote=update.evidence.strip(),
        ))
    items = [update.item] if update else list(state.review_draft.unresolved_items)
    return StaffSummaryDraft(
        summary="A parent or guardian reported an appointment-preparation issue requiring staff review. Please verify the original report and determine appropriate follow-up.",
        reported_details=details,
        review_items=items,
    )
