from __future__ import annotations

from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Min, Q
from django.utils import timezone

from .models import Ticket


def _count_by_choice(queryset, *, field_name: str, choices) -> dict[str, int]:
    counts = {value: 0 for value, _label in choices}
    for row in queryset.values(field_name).annotate(total=Count("id")):
        counts[row[field_name]] = row["total"]
    return counts


def build_ticket_summary(queryset) -> dict[str, object]:
    now = timezone.now()
    resolved_status_values = Ticket.resolved_statuses()
    active_filter = ~Q(status__in=resolved_status_values)
    aggregates = queryset.aggregate(
        visible_tickets=Count("id"),
        active_tickets=Count("id", filter=active_filter),
        resolved_tickets=Count("id", filter=Q(status__in=resolved_status_values)),
        unassigned_tickets=Count("id", filter=active_filter & Q(assigned_to__isnull=True)),
        unanswered_tickets=Count("id", filter=active_filter & Q(first_response_at__isnull=True)),
        overdue_tickets=Count("id", filter=active_filter & Q(sla_deadline_at__lt=now)),
    )

    return {
        "visible_tickets": aggregates["visible_tickets"],
        "active_tickets": aggregates["active_tickets"],
        "resolved_tickets": aggregates["resolved_tickets"],
        "unassigned_tickets": aggregates["unassigned_tickets"],
        "unanswered_tickets": aggregates["unanswered_tickets"],
        "overdue_tickets": aggregates["overdue_tickets"],
        "by_status": _count_by_choice(
            queryset,
            field_name="status",
            choices=Ticket.Status.choices,
        ),
        "by_priority": _count_by_choice(
            queryset,
            field_name="priority",
            choices=Ticket.Priority.choices,
        ),
    }


def _average_hours(duration: timedelta | None) -> float | None:
    if duration is None:
        return None
    return round(duration.total_seconds() / 3600, 2)


def build_ticket_analytics(queryset) -> dict[str, object]:
    now = timezone.now()
    resolved_status_values = Ticket.resolved_statuses()
    active_queryset = queryset.exclude(status__in=resolved_status_values)
    duration_expression = {
        "response": ExpressionWrapper(
            F("first_response_at") - F("created_at"),
            output_field=DurationField(),
        ),
        "resolution": ExpressionWrapper(
            F("resolved_at") - F("created_at"),
            output_field=DurationField(),
        ),
    }
    avg_first_response_duration = (
        queryset.filter(first_response_at__isnull=False)
        .annotate(duration=duration_expression["response"])
        .aggregate(value=Avg("duration"))["value"]
    )
    avg_resolution_duration = (
        queryset.filter(resolved_at__isnull=False)
        .annotate(duration=duration_expression["resolution"])
        .aggregate(value=Avg("duration"))["value"]
    )
    sla_aggregates = queryset.aggregate(
        resolved_within_sla=Count(
            "id",
            filter=Q(resolved_at__isnull=False)
            & Q(sla_deadline_at__isnull=False)
            & Q(resolved_at__lte=F("sla_deadline_at")),
        ),
        resolved_outside_sla=Count(
            "id",
            filter=Q(resolved_at__isnull=False)
            & Q(sla_deadline_at__isnull=False)
            & Q(resolved_at__gt=F("sla_deadline_at")),
        ),
    )
    oldest_overdue_deadline = active_queryset.filter(sla_deadline_at__lt=now).aggregate(
        value=Min("sla_deadline_at")
    )["value"]
    oldest_overdue_hours = None
    if oldest_overdue_deadline is not None:
        oldest_overdue_hours = round((now - oldest_overdue_deadline).total_seconds() / 3600, 2)

    workload = list(
        active_queryset.filter(assigned_to__isnull=False)
        .values("assigned_to_id", "assigned_to__username")
        .annotate(active_tickets=Count("id"))
        .order_by("-active_tickets", "assigned_to__username")
    )

    return {
        "avg_first_response_hours": _average_hours(avg_first_response_duration),
        "avg_resolution_hours": _average_hours(avg_resolution_duration),
        "resolved_within_sla": sla_aggregates["resolved_within_sla"],
        "resolved_outside_sla": sla_aggregates["resolved_outside_sla"],
        "oldest_overdue_hours": oldest_overdue_hours,
        "active_workload_by_assignee": [
            {
                "assigned_to": row["assigned_to_id"],
                "assigned_to_username": row["assigned_to__username"],
                "active_tickets": row["active_tickets"],
            }
            for row in workload
        ],
    }
