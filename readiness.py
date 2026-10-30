from models import Appointment, ItemName


def find_unresolved_items(appointment: Appointment) -> list[ItemName]:
    """List tracked items that are not reported confirmed. No AI or changes."""
    checklist = {
        "transportation": appointment.transportation,
        "registration": appointment.registration,
        "paperwork": appointment.paperwork,
    }

    unresolved: list[ItemName] = []
    for name, item in checklist.items():
        if item.status != "confirmed":
            unresolved.append(name)

    return unresolved
