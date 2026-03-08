from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .audit import TicketSnapshot
from .models import Ticket


def resolved_statuses() -> tuple[str, ...]:
    return Ticket.resolved_statuses()


def calculate_sla_deadline(*, priority: str, start_at=None):
    started_at = start_at or timezone.now()
    hours = settings.TICKET_SLA_HOURS.get(
        priority,
        settings.TICKET_SLA_HOURS[Ticket.Priority.MEDIUM],
    )
    return started_at + timedelta(hours=hours)


def apply_sla_on_create(*, ticket: Ticket, actor_is_support: bool) -> list[str]:
    changed_fields = ["sla_deadline_at"]
    timestamp = ticket.created_at or timezone.now()
    ticket.sla_deadline_at = calculate_sla_deadline(priority=ticket.priority, start_at=timestamp)

    if actor_is_support and (
        ticket.assigned_to_id is not None or ticket.status != Ticket.Status.NEW
    ):
        ticket.first_response_at = timestamp
        changed_fields.append("first_response_at")

    if ticket.status in resolved_statuses():
        ticket.resolved_at = timestamp
        changed_fields.append("resolved_at")

    return changed_fields


def apply_sla_on_update(
    *,
    ticket: Ticket,
    before: TicketSnapshot,
    actor_is_support: bool,
) -> list[str]:
    changed_fields: list[str] = []
    now = timezone.now()

    if ticket.sla_deadline_at is None or before.priority != ticket.priority:
        ticket.sla_deadline_at = calculate_sla_deadline(
            priority=ticket.priority,
            start_at=ticket.created_at or now,
        )
        changed_fields.append("sla_deadline_at")

    support_work_started = actor_is_support and (
        before.status != ticket.status or before.assigned_to_id != ticket.assigned_to_id
    )
    if support_work_started and ticket.first_response_at is None:
        ticket.first_response_at = now
        changed_fields.append("first_response_at")

    status_is_resolved = ticket.status in resolved_statuses()
    if status_is_resolved and ticket.resolved_at is None:
        ticket.resolved_at = now
        changed_fields.append("resolved_at")
    elif not status_is_resolved and ticket.resolved_at is not None:
        ticket.resolved_at = None
        changed_fields.append("resolved_at")

    return changed_fields
