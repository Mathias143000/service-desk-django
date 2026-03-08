from __future__ import annotations

from django.utils import timezone
from django_filters import rest_framework as filters

from .models import Ticket


class TicketFilter(filters.FilterSet):
    is_overdue = filters.BooleanFilter(method="filter_is_overdue")
    due_before = filters.IsoDateTimeFilter(field_name="sla_deadline_at", lookup_expr="lte")
    due_after = filters.IsoDateTimeFilter(field_name="sla_deadline_at", lookup_expr="gte")

    class Meta:
        model = Ticket
        fields = (
            "status",
            "priority",
            "assigned_to",
            "created_by",
            "is_overdue",
            "due_before",
            "due_after",
        )

    def filter_is_overdue(self, queryset, _name, value):
        if value is None:
            return queryset

        overdue_queryset = queryset.overdue(at=timezone.now())
        if value:
            return overdue_queryset
        return queryset.exclude(pk__in=overdue_queryset.values("pk"))
