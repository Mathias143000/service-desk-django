from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import Ticket
from tickets.sla import calculate_sla_deadline

User = get_user_model()


class Command(BaseCommand):
    help = "Create demo users and tickets for local portfolio review."

    def handle(self, *args, **options):
        now = timezone.now()

        user_specs = [
            ("alex", "pass12345", False),
            ("maria", "pass12345", False),
            ("support", "pass12345", True),
        ]

        users: dict[str, User] = {}
        for username, password, is_staff in user_specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": is_staff},
            )
            if user.is_staff != is_staff:
                user.is_staff = is_staff
                user.save(update_fields=["is_staff"])
            user.set_password(password)
            user.save(update_fields=["password"])
            users[username] = user
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} user: {username}")

        ticket_specs = [
            {
                "title": "VPN access is not working",
                "description": "User cannot connect after password reset.",
                "created_by": users["alex"],
                "assigned_to": users["support"],
                "status": Ticket.Status.IN_PROGRESS,
                "priority": Ticket.Priority.HIGH,
                "first_response_at": now - timedelta(hours=2),
                "resolved_at": None,
                "sla_deadline_at": now + timedelta(hours=6),
            },
            {
                "title": "Email signature update request",
                "description": "Need to update job title in signature.",
                "created_by": users["maria"],
                "assigned_to": None,
                "status": Ticket.Status.NEW,
                "priority": Ticket.Priority.LOW,
                "first_response_at": None,
                "resolved_at": None,
                "sla_deadline_at": now + timedelta(hours=48),
            },
            {
                "title": "Production 500 on customer portal",
                "description": "Critical incident reported by support team.",
                "created_by": users["alex"],
                "assigned_to": users["support"],
                "status": Ticket.Status.NEW,
                "priority": Ticket.Priority.CRITICAL,
                "first_response_at": None,
                "resolved_at": None,
                "sla_deadline_at": now - timedelta(minutes=30),
            },
            {
                "title": "Printer issue on floor 2",
                "description": "Ticket resolved after driver reinstall.",
                "created_by": users["maria"],
                "assigned_to": users["support"],
                "status": Ticket.Status.CLOSED,
                "priority": Ticket.Priority.MEDIUM,
                "first_response_at": now - timedelta(hours=8),
                "resolved_at": now - timedelta(hours=1),
                "sla_deadline_at": calculate_sla_deadline(
                    priority=Ticket.Priority.MEDIUM,
                    start_at=now - timedelta(hours=10),
                ),
            },
        ]

        for spec in ticket_specs:
            ticket, created = Ticket.objects.update_or_create(
                title=spec["title"],
                created_by=spec["created_by"],
                defaults={
                    "description": spec["description"],
                    "assigned_to": spec["assigned_to"],
                    "status": spec["status"],
                    "priority": spec["priority"],
                    "first_response_at": spec["first_response_at"],
                    "resolved_at": spec["resolved_at"],
                    "sla_deadline_at": spec["sla_deadline_at"],
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} ticket: #{ticket.id} {ticket.title}")

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write("Credentials: alex/pass12345, maria/pass12345, support/pass12345")
