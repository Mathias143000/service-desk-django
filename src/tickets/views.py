from __future__ import annotations

import csv

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .audit import log_ticket_created, log_ticket_updated, snapshot_ticket
from .filters import TicketFilter
from .models import Ticket
from .permissions import TicketPermission, is_support
from .reporting import build_ticket_analytics, build_ticket_summary
from .serializers import (
    AuditLogSerializer,
    SupportTicketCreateSerializer,
    SupportTicketUpdateSerializer,
    TicketSerializer,
    UserTicketCreateSerializer,
    UserTicketUpdateSerializer,
)
from .sla import apply_sla_on_create, apply_sla_on_update


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [TicketPermission]
    queryset = Ticket.objects.select_related("created_by", "assigned_to")

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TicketFilter
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "updated_at", "priority", "status", "sla_deadline_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        user = self.request.user
        if is_support(user):
            return self.queryset
        return self.queryset.filter(created_by=user)

    def get_serializer_class(self):
        user = getattr(self.request, "user", None)
        if self.action == "create":
            return SupportTicketCreateSerializer if is_support(user) else UserTicketCreateSerializer
        if self.action in {"update", "partial_update"}:
            return SupportTicketUpdateSerializer if is_support(user) else UserTicketUpdateSerializer
        return TicketSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        ticket = serializer.save()
        updated_fields = apply_sla_on_create(
            ticket=ticket,
            actor_is_support=is_support(self.request.user),
        )
        ticket.save(update_fields=updated_fields)
        log_ticket_created(actor=self.request.user, ticket=ticket)

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        ticket = self.get_object()

        if not is_support(user) and ticket.created_by_id != user.id:
            raise PermissionDenied("You can only update your own tickets.")

        before = snapshot_ticket(ticket)

        updated = serializer.save()
        updated_fields = apply_sla_on_update(
            ticket=updated,
            before=before,
            actor_is_support=is_support(user),
        )
        if updated_fields:
            updated.save(update_fields=updated_fields)
        after = snapshot_ticket(updated)
        log_ticket_updated(actor=user, ticket=updated, before=before, after=after)

    @action(detail=True, methods=["get"], url_path="audit-log")
    def audit_log(self, request, pk=None):
        ticket = self.get_object()
        queryset = ticket.audit_logs.select_related("actor", "ticket")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AuditLogSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset()).select_related(
            "created_by",
            "assigned_to",
        )

        timestamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="tickets-{timestamp}.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "title",
                "status",
                "priority",
                "created_by",
                "assigned_to",
                "sla_deadline_at",
                "first_response_at",
                "resolved_at",
                "is_overdue",
                "created_at",
                "updated_at",
            ]
        )

        for ticket in queryset.iterator():
            writer.writerow(
                [
                    ticket.id,
                    ticket.title,
                    ticket.status,
                    ticket.priority,
                    ticket.created_by.username,
                    ticket.assigned_to.username if ticket.assigned_to else "",
                    ticket.sla_deadline_at.isoformat() if ticket.sla_deadline_at else "",
                    ticket.first_response_at.isoformat() if ticket.first_response_at else "",
                    ticket.resolved_at.isoformat() if ticket.resolved_at else "",
                    str(ticket.is_overdue).lower(),
                    ticket.created_at.isoformat(),
                    ticket.updated_at.isoformat(),
                ]
            )

        return response

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(build_ticket_summary(queryset))

    @action(detail=False, methods=["get"], url_path="analytics")
    def analytics(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(build_ticket_analytics(queryset))
