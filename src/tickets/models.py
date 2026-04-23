from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class TicketQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(status__in=self.model.resolved_statuses())

    def overdue(self, *, at=None):
        timestamp = at or timezone.now()
        return self.active().filter(sla_deadline_at__lt=timestamp)


class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In progress"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tickets",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    sla_deadline_at = models.DateTimeField(null=True, blank=True, db_index=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notification_stub_sent_at = models.DateTimeField(null=True, blank=True)
    notification_stub_action = models.CharField(max_length=40, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TicketQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("created_by", "-created_at")),
            models.Index(fields=("assigned_to", "-created_at")),
        ]

    @classmethod
    def resolved_statuses(cls) -> tuple[str, ...]:
        return (cls.Status.CLOSED, cls.Status.REJECTED)

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.sla_deadline_at
            and self.status not in self.resolved_statuses()
            and self.sla_deadline_at < timezone.now()
        )

    def __str__(self) -> str:
        return f"#{self.id} {self.title}"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        TICKET_CREATED = "ticket_created", "Ticket created"
        STATUS_CHANGED = "status_changed", "Status changed"
        ASSIGNED_CHANGED = "assigned_changed", "Assigned changed"
        PRIORITY_CHANGED = "priority_changed", "Priority changed"
        TICKET_UPDATED = "ticket_updated", "Ticket updated"

    action = models.CharField(max_length=40, choices=Action.choices)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )

    # Optional old/new fields (enough for simple auditing + swagger display)
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20, blank=True, default="")
    from_priority = models.CharField(max_length=20, blank=True, default="")
    to_priority = models.CharField(max_length=20, blank=True, default="")
    from_assigned_to = models.PositiveBigIntegerField(null=True, blank=True)
    to_assigned_to = models.PositiveBigIntegerField(null=True, blank=True)

    meta = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("ticket", "-created_at")),
            models.Index(fields=("actor", "-created_at")),
            models.Index(fields=("action", "-created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.action} ticket={self.ticket_id}"
