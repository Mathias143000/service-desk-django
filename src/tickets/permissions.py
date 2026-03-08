from __future__ import annotations

from rest_framework.permissions import BasePermission


def is_support(user) -> bool:
    """Support role check.

    Variant A (default): is_staff
    Variant B: group named "support"
    """
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_staff or user.groups.filter(name="support").exists())


class TicketPermission(BasePermission):
    """Role-aware permissions for TicketViewSet."""

    allowed_actions = {
        "list",
        "retrieve",
        "create",
        "update",
        "partial_update",
        "audit_log",
        "export",
        "summary",
        "analytics",
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if view.action in self.allowed_actions:
            return True

        # Deny by default to avoid accidental access to future custom actions.
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_support(user):
            return True

        # Regular user: can only access their own tickets.
        return getattr(obj, "created_by_id", None) == user.id
