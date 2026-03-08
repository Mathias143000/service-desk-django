from django.contrib import admin

from .models import AuditLog, Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
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
    )
    list_filter = ("status", "priority", "created_at", "sla_deadline_at")
    search_fields = ("title", "description", "created_by__username", "assigned_to__username")
    ordering = ("-created_at",)
    list_select_related = ("created_by", "assigned_to")
    readonly_fields = (
        "sla_deadline_at",
        "first_response_at",
        "resolved_at",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("created_by", "assigned_to")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "actor",
        "ticket",
        "from_status",
        "to_status",
        "from_priority",
        "to_priority",
        "from_assigned_to",
        "to_assigned_to",
        "created_at",
    )
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "ticket__title")
    ordering = ("-created_at",)
    list_select_related = ("actor", "ticket")
    readonly_fields = (
        "action",
        "actor",
        "ticket",
        "from_status",
        "to_status",
        "from_priority",
        "to_priority",
        "from_assigned_to",
        "to_assigned_to",
        "meta",
        "created_at",
    )
