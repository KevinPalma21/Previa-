"""Pre-model scope denial, recognized clinical review, and logistics routing."""

import re
from typing import Literal


_CLINICAL_TERMS = re.compile(
    r"\b(?:medicines?|medications?|meds?|drugs?|pills?|dos(?:e|es|age)|"
    r"prescriptions?|antibiotics?|tylenol|acetaminophen|ibuprofen|aspirin|"
    r"zyrtec|cetirizine|benadryl|insulin|inhalers?|"
    r"treatments?|symptoms?|fever|vomit(?:ing)?|pain|allerg(?:y|ies)|"
    r"side[ -]?effects?)\b",
    re.IGNORECASE,
)
_CLINICAL_ACTIONS = re.compile(
    r"\b(?:should|can|may)\s+(?:i|we|my child|my daughter|my son|they|she|he)\s+"
    r"(?:take|give|stop|start|skip)\b|\b(?:do|should|can)\s+i\s+(?:need\s+to\s+)?take\b|"
    r"\b(?:stop|start|skip)\s+taking\b",
    re.IGNORECASE,
)
_LOGISTICS_TERMS = re.compile(
    r"\b(?:rides?|driv(?:e|er|ing)|transportation|park(?:ing)?|garages?|directions?|"
    r"registration|paperwork|forms?|referrals?|insurance|mychart|check[ -]?in|checklist|bring)\b",
    re.IGNORECASE,
)
_DENIED_INTENTS = re.compile(
    r"\b(?:equations?|algebra|homework|jokes?|poems?|recipes?|weather|"
    r"sports scores?|stock prices?|cryptocurrency)\b|"
    r"\b(?:ignore|bypass|override)\b.{0,80}\b(?:rules?|instructions?|polic(?:y|ies)|guardrails?)\b|"
    r"\b(?:social[ -]?security|ssns?|api[ _-]?keys?|system[ _-]?prompt|credentials)\b|"
    r"\b(?:show|reveal|give|list|send|retrieve|access|get)\b.{0,80}\bpasswords?\b|"
    r"\b(?:all|other|another)\s+(?:the\s+)?patients?['’s]*\b.{0,80}\b(?:records?|data|details|names)\b|"
    r"\b(?:records?|data|details|names)\b.{0,50}\b(?:all|other|another)\s+patients?\b",
    re.IGNORECASE | re.DOTALL,
)


def needs_clinical_review(message: str) -> bool:
    """Flag common clinical wording before any AI role sees the message.

    This is a cautious demo gate, not a complete medical-question classifier.
    """
    return bool(_CLINICAL_TERMS.search(message) or _CLINICAL_ACTIONS.search(message))


def pre_model_route(message: str) -> Literal["logistics", "clinical_review", "denied"]:
    """Deny unsupported requests without invoking models or creating tasks.

    Explicit unrelated/unauthorized intents cannot gain access just by adding a
    logistics keyword. Phrase matching remains a limited prototype screen.
    """
    if _DENIED_INTENTS.search(message):
        return "denied"
    if needs_clinical_review(message):
        return "clinical_review"
    if _LOGISTICS_TERMS.search(message):
        return "logistics"
    return "denied"
