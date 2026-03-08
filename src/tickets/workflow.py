from __future__ import annotations

from rest_framework import serializers

from .models import Ticket

SUPPORT_STATUS_TRANSITIONS: dict[str, set[str]] = {
    Ticket.Status.NEW: {
        Ticket.Status.NEW,
        Ticket.Status.IN_PROGRESS,
        Ticket.Status.CLOSED,
        Ticket.Status.REJECTED,
    },
    Ticket.Status.IN_PROGRESS: {
        Ticket.Status.IN_PROGRESS,
        Ticket.Status.CLOSED,
        Ticket.Status.REJECTED,
    },
    Ticket.Status.CLOSED: {
        Ticket.Status.CLOSED,
        Ticket.Status.IN_PROGRESS,
    },
    Ticket.Status.REJECTED: {
        Ticket.Status.REJECTED,
        Ticket.Status.IN_PROGRESS,
    },
}


def validate_support_status_transition(*, current_status: str, next_status: str) -> None:
    allowed_statuses = SUPPORT_STATUS_TRANSITIONS[current_status]
    if next_status not in allowed_statuses:
        raise serializers.ValidationError(
            {
                "status": (
                    f"Transition from '{current_status}' to '{next_status}' is not allowed."
                )
            }
        )


def validate_assignment_for_status(*, status: str, assigned_to) -> None:
    if status == Ticket.Status.IN_PROGRESS and assigned_to is None:
        raise serializers.ValidationError(
            {"assigned_to": "An in-progress ticket must be assigned to a support user."}
        )
