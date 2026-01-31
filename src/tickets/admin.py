from django.contrib import admin
from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "owner", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description", "owner__username")
    ordering = ("-created_at",)
