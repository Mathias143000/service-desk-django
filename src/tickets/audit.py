from __future__ import annotations

from dataclasses import dataclass

from .models import AuditLog, Ticket


@dataclass(frozen=True)
class TicketSnapshot:
    status: str
    priority: str
    assigned_to_id: int | None
    title: str
    description: str


def snapshot_ticket(ticket: Ticket) -> TicketSnapshot:
    return TicketSnapshot(
        status=ticket.status,
        priority=ticket.priority,
        assigned_to_id=ticket.assigned_to_id,
        title=ticket.title,
        description=ticket.description,
    )


def log_ticket_created(*, actor, ticket: Ticket) -> None:
    AuditLog.objects.create(
        action=AuditLog.Action.TICKET_CREATED,
        actor=actor,
        ticket=ticket,
        to_status=ticket.status,
        to_priority=ticket.priority,
        to_assigned_to=ticket.assigned_to_id,
    )


def log_ticket_updated(
    *,
    actor,
    ticket: Ticket,
    before: TicketSnapshot,
    after: TicketSnapshot,
) -> None:
    entries: list[AuditLog] = []

    if before.status != after.status:
        entries.append(
            AuditLog(
                action=AuditLog.Action.STATUS_CHANGED,
                actor=actor,
                ticket=ticket,
                from_status=before.status,
                to_status=after.status,
            )
        )

    if before.priority != after.priority:
        entries.append(
            AuditLog(
                action=AuditLog.Action.PRIORITY_CHANGED,
                actor=actor,
                ticket=ticket,
                from_priority=before.priority,
                to_priority=after.priority,
            )
        )

    if before.assigned_to_id != after.assigned_to_id:
        entries.append(
            AuditLog(
                action=AuditLog.Action.ASSIGNED_CHANGED,
                actor=actor,
                ticket=ticket,
                from_assigned_to=before.assigned_to_id,
                to_assigned_to=after.assigned_to_id,
            )
        )

    if before.title != after.title or before.description != after.description:
        entries.append(
            AuditLog(
                action=AuditLog.Action.TICKET_UPDATED,
                actor=actor,
                ticket=ticket,
                meta={
                    "title_changed": before.title != after.title,
                    "description_changed": before.description != after.description,
                },
            )
        )

    if entries:
        AuditLog.objects.bulk_create(entries)
