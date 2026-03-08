from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AuditLog, Ticket
from .permissions import is_support
from .workflow import validate_assignment_for_status, validate_support_status_transition

User = get_user_model()


class TicketSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    assigned_to_username = serializers.CharField(source="assigned_to.username", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "created_by",
            "created_by_username",
            "assigned_to",
            "assigned_to_username",
            "sla_deadline_at",
            "first_response_at",
            "resolved_at",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_by_username",
            "assigned_to_username",
            "sla_deadline_at",
            "first_response_at",
            "resolved_at",
            "is_overdue",
            "created_at",
            "updated_at",
        ]


class TicketChoiceValidationMixin:
    def validate_status(self, value: str) -> str:
        allowed = {choice for choice, _ in Ticket.Status.choices}
        if value not in allowed:
            raise serializers.ValidationError("Invalid status.")
        return value

    def validate_priority(self, value: str) -> str:
        allowed = {choice for choice, _ in Ticket.Priority.choices}
        if value not in allowed:
            raise serializers.ValidationError("Invalid priority.")
        return value

    def validate_assigned_to(self, value):
        if value is not None and not is_support(value):
            raise serializers.ValidationError("Ticket can be assigned only to support users.")
        return value


class UserTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "sla_deadline_at",
            "first_response_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sla_deadline_at",
            "first_response_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        forbidden = {"status", "priority", "assigned_to", "created_by"}
        provided = sorted(forbidden.intersection(self.initial_data))
        if provided:
            raise serializers.ValidationError(
                {field: "You are not allowed to set this field." for field in provided}
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class SupportTicketCreateSerializer(TicketChoiceValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "assigned_to",
            "sla_deadline_at",
            "first_response_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sla_deadline_at",
            "first_response_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        status = attrs.get("status", Ticket.Status.NEW)
        assigned_to = attrs.get("assigned_to")
        validate_assignment_for_status(status=status, assigned_to=assigned_to)
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class UserTicketUpdateSerializer(serializers.ModelSerializer):
    """Regular user can update only title/description (optionally close ticket)."""

    class Meta:
        model = Ticket
        fields = ["title", "description", "status"]
        extra_kwargs = {
            "status": {"required": False},
            "title": {"required": False},
            "description": {"required": False},
        }

    def validate_status(self, value: str) -> str:
        if value != Ticket.Status.CLOSED:
            raise serializers.ValidationError("You can only set status=closed.")
        return value

    def validate(self, attrs):
        forbidden = {"priority", "assigned_to", "created_by"}
        provided = sorted(forbidden.intersection(self.initial_data))
        if provided:
            raise serializers.ValidationError(
                {field: "You are not allowed to set this field." for field in provided}
            )
        return attrs


class SupportTicketUpdateSerializer(TicketChoiceValidationMixin, serializers.ModelSerializer):
    """Support can update service fields and also edit title/description."""

    class Meta:
        model = Ticket
        fields = ["title", "description", "status", "priority", "assigned_to"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        ticket = self.instance
        next_status = attrs.get("status", ticket.status)
        next_assigned_to = attrs.get("assigned_to", ticket.assigned_to)

        validate_support_status_transition(
            current_status=ticket.status,
            next_status=next_status,
        )
        validate_assignment_for_status(
            status=next_status,
            assigned_to=next_assigned_to,
        )
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "actor",
            "actor_username",
            "ticket",
            "from_status",
            "to_status",
            "from_priority",
            "to_priority",
            "from_assigned_to",
            "to_assigned_to",
            "meta",
            "created_at",
        ]
        read_only_fields = fields
