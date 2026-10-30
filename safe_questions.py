"""Fixed logistics questions that are eligible for caregiver display."""

from models import ItemName


QUESTIONS_BY_ITEM: dict[ItemName, str] = {
    "transportation": "Have you been able to confirm a ride for the appointment?",
    "registration": "Have you been able to complete registration?",
    "paperwork": "Have you been able to complete the paperwork?",
}

APPROVED_QUESTIONS = set(QUESTIONS_BY_ITEM.values())
