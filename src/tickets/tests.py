from __future__ import annotations

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import AuditLog, Ticket

User = get_user_model()


class TicketAPITests(APITestCase):
    token_url = "/api/auth/token/"
    tickets_url = "/api/tickets/"

    def setUp(self):
        self.user1 = User.objects.create_user(username="u1", password="pass12345")
        self.user2 = User.objects.create_user(username="u2", password="pass12345")
        self.support = User.objects.create_user(
            username="support",
            password="pass12345",
            is_staff=True,
        )

        self.t1 = Ticket.objects.create(
            title="My ticket",
            description="desc",
            created_by=self.user1,
        )
        self.t2 = Ticket.objects.create(
            title="Other ticket",
            description="desc",
            created_by=self.user2,
        )

    def _auth(self, username: str, password: str):
        response = self.client.post(
            self.token_url,
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_jwt_can_access_tickets(self):
        self._auth("u1", "pass12345")
        response = self.client.get(self.tickets_url)
        self.assertEqual(response.status_code, 200)

    def test_user_can_create_ticket_with_default_service_fields(self):
        self._auth("u1", "pass12345")
        response = self.client.post(
            self.tickets_url,
            {"title": "New", "description": "D"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        ticket = Ticket.objects.get(id=response.data["id"])
        self.assertEqual(ticket.created_by, self.user1)
        self.assertEqual(ticket.priority, Ticket.Priority.MEDIUM)
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertIsNotNone(ticket.sla_deadline_at)
        self.assertIsNone(ticket.first_response_at)
        self.assertIsNone(ticket.resolved_at)

    def test_user_cannot_set_service_fields_on_create(self):
        self._auth("u1", "pass12345")
        response = self.client.post(
            self.tickets_url,
            {
                "title": "Cannot override service fields",
                "description": "D",
                "status": Ticket.Status.CLOSED,
                "priority": Ticket.Priority.CRITICAL,
                "assigned_to": self.support.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.data)
        self.assertIn("priority", response.data)
        self.assertIn("assigned_to", response.data)

    def test_support_can_create_ticket_with_service_fields(self):
        self._auth("support", "pass12345")
        response = self.client.post(
            self.tickets_url,
            {
                "title": "Support ticket",
                "description": "D",
                "status": Ticket.Status.IN_PROGRESS,
                "priority": Ticket.Priority.HIGH,
                "assigned_to": self.support.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        ticket = Ticket.objects.get(id=response.data["id"])
        self.assertEqual(ticket.created_by, self.support)
        self.assertEqual(ticket.status, Ticket.Status.IN_PROGRESS)
        self.assertEqual(ticket.priority, Ticket.Priority.HIGH)
        self.assertEqual(ticket.assigned_to, self.support)

    def test_support_cannot_create_in_progress_ticket_without_assignee(self):
        self._auth("support", "pass12345")
        response = self.client.post(
            self.tickets_url,
            {
                "title": "Broken workflow",
                "description": "D",
                "status": Ticket.Status.IN_PROGRESS,
                "priority": Ticket.Priority.HIGH,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_to", response.data)

    def test_support_cannot_assign_ticket_to_regular_user(self):
        self._auth("support", "pass12345")
        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {"assigned_to": self.user2.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_to", response.data)

    def test_support_cannot_move_ticket_to_in_progress_without_assignee(self):
        self._auth("support", "pass12345")
        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {"status": Ticket.Status.IN_PROGRESS},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_to", response.data)

    def test_support_workflow_sets_first_response_and_resolved_at(self):
        self._auth("support", "pass12345")
        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {
                "status": Ticket.Status.IN_PROGRESS,
                "assigned_to": self.support.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.t1.refresh_from_db()
        self.assertIsNotNone(self.t1.first_response_at)
        self.assertIsNone(self.t1.resolved_at)

        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {"status": Ticket.Status.CLOSED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.t1.refresh_from_db()
        self.assertIsNotNone(self.t1.resolved_at)

    def test_support_cannot_reopen_resolved_ticket_to_new_status(self):
        self.t1.status = Ticket.Status.CLOSED
        self.t1.resolved_at = timezone.now()
        self.t1.save(update_fields=["status", "resolved_at"])

        self._auth("support", "pass12345")
        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {"status": Ticket.Status.NEW},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.data)

    def test_user_list_only_own_tickets(self):
        self._auth("u1", "pass12345")
        response = self.client.get(self.tickets_url)
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(self.t1.id, ids)
        self.assertNotIn(self.t2.id, ids)

    def test_user_cannot_retrieve_foreign_ticket(self):
        self._auth("u1", "pass12345")
        response = self.client.get(f"{self.tickets_url}{self.t2.id}/")
        self.assertEqual(response.status_code, 404)

    def test_user_can_only_close_ticket_as_status_update(self):
        self._auth("u1", "pass12345")
        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {"status": Ticket.Status.IN_PROGRESS},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.data)

        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {"status": Ticket.Status.CLOSED},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, Ticket.Status.CLOSED)

    def test_support_sees_all_tickets(self):
        self._auth("support", "pass12345")
        response = self.client.get(self.tickets_url)
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(self.t1.id, ids)
        self.assertIn(self.t2.id, ids)

    def test_support_filter_by_created_by(self):
        self._auth("support", "pass12345")
        response = self.client.get(self.tickets_url, {"created_by": self.user1.id})
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [self.t1.id])

    def test_delete_ticket_is_forbidden(self):
        self._auth("support", "pass12345")
        response = self.client.delete(f"{self.tickets_url}{self.t1.id}/")
        self.assertEqual(response.status_code, 403)

    def test_auditlog_created_on_status_changed(self):
        self._auth("support", "pass12345")
        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {
                "status": Ticket.Status.IN_PROGRESS,
                "assigned_to": self.support.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(
                ticket=self.t1,
                action=AuditLog.Action.STATUS_CHANGED,
            ).exists()
        )

    def test_auditlog_created_on_title_change(self):
        self._auth("support", "pass12345")
        response = self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {"title": "Updated title"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(
                ticket=self.t1,
                action=AuditLog.Action.TICKET_UPDATED,
            ).exists()
        )

    def test_user_can_view_own_ticket_audit_log(self):
        self._auth("support", "pass12345")
        self.client.patch(
            f"{self.tickets_url}{self.t1.id}/",
            {
                "status": Ticket.Status.IN_PROGRESS,
                "assigned_to": self.support.id,
            },
            format="json",
        )

        self._auth("u1", "pass12345")
        response = self.client.get(f"{self.tickets_url}{self.t1.id}/audit-log/")

        self.assertEqual(response.status_code, 200)
        actions = {item["action"] for item in response.data["results"]}
        self.assertIn(AuditLog.Action.STATUS_CHANGED, actions)
        self.assertTrue(all(item["ticket"] == self.t1.id for item in response.data["results"]))

    def test_user_cannot_view_foreign_ticket_audit_log(self):
        self._auth("u1", "pass12345")
        response = self.client.get(f"{self.tickets_url}{self.t2.id}/audit-log/")
        self.assertEqual(response.status_code, 404)

    def test_export_returns_csv_with_visible_tickets_only(self):
        self._auth("u1", "pass12345")
        response = self.client.get(f"{self.tickets_url}export/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        payload = response.content.decode("utf-8")
        self.assertIn(
            "id,title,status,priority,created_by,assigned_to,sla_deadline_at,first_response_at,resolved_at,is_overdue,created_at,updated_at",
            payload,
        )
        self.assertIn("My ticket", payload)
        self.assertNotIn("Other ticket", payload)

    def test_user_can_filter_overdue_tickets(self):
        self.t1.sla_deadline_at = timezone.now() - timedelta(hours=1)
        self.t1.save(update_fields=["sla_deadline_at"])
        self.t2.sla_deadline_at = timezone.now() + timedelta(hours=1)
        self.t2.save(update_fields=["sla_deadline_at"])

        self._auth("u1", "pass12345")
        response = self.client.get(self.tickets_url, {"is_overdue": "true"})

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [self.t1.id])

    def test_summary_returns_visible_ticket_aggregates(self):
        self.t1.sla_deadline_at = timezone.now() - timedelta(hours=2)
        self.t1.save(update_fields=["sla_deadline_at"])

        self._auth("u1", "pass12345")
        response = self.client.get(f"{self.tickets_url}summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["visible_tickets"], 1)
        self.assertEqual(response.data["active_tickets"], 1)
        self.assertEqual(response.data["unassigned_tickets"], 1)
        self.assertEqual(response.data["unanswered_tickets"], 1)
        self.assertEqual(response.data["overdue_tickets"], 1)
        self.assertEqual(response.data["by_status"][Ticket.Status.NEW], 1)
        self.assertEqual(response.data["by_priority"][Ticket.Priority.MEDIUM], 1)

    def test_analytics_returns_average_durations_and_workload(self):
        reference_now = timezone.now()
        self.t1.created_at = reference_now - timedelta(hours=10)
        self.t1.assigned_to = self.support
        self.t1.status = Ticket.Status.CLOSED
        self.t1.first_response_at = self.t1.created_at + timedelta(hours=2)
        self.t1.resolved_at = self.t1.created_at + timedelta(hours=6)
        self.t1.sla_deadline_at = self.t1.created_at + timedelta(hours=8)
        self.t1.save(
            update_fields=[
                "created_at",
                "assigned_to",
                "status",
                "first_response_at",
                "resolved_at",
                "sla_deadline_at",
            ]
        )

        self.t2.created_at = reference_now - timedelta(hours=2)
        self.t2.assigned_to = self.support
        self.t2.status = Ticket.Status.IN_PROGRESS
        self.t2.sla_deadline_at = reference_now - timedelta(hours=1)
        self.t2.first_response_at = self.t2.created_at + timedelta(minutes=30)
        self.t2.save(
            update_fields=[
                "created_at",
                "assigned_to",
                "status",
                "sla_deadline_at",
                "first_response_at",
            ]
        )

        self._auth("support", "pass12345")
        response = self.client.get(f"{self.tickets_url}analytics/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["avg_first_response_hours"], 1.25)
        self.assertEqual(response.data["avg_resolution_hours"], 6.0)
        self.assertEqual(response.data["resolved_within_sla"], 1)
        self.assertEqual(response.data["resolved_outside_sla"], 0)
        self.assertEqual(len(response.data["active_workload_by_assignee"]), 1)
        self.assertEqual(response.data["active_workload_by_assignee"][0]["active_tickets"], 1)
        self.assertGreater(response.data["oldest_overdue_hours"], 0)


class HealthCheckTests(APITestCase):
    def test_healthcheck_returns_app_and_database_status(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["database"], "ok")
        self.assertEqual(response.data["version"], settings.APP_VERSION)
        self.assertIn("timestamp", response.data)

    @patch("config.views.database_is_available", return_value=False)
    def test_healthcheck_returns_503_when_database_is_unavailable(self, _database_is_available):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["status"], "error")
        self.assertEqual(response.data["database"], "unavailable")


class DemoSeedCommandTests(APITestCase):
    def test_seed_demo_data_command_is_idempotent(self):
        output = StringIO()

        call_command("seed_demo_data", stdout=output)
        call_command("seed_demo_data", stdout=output)

        self.assertTrue(User.objects.filter(username="support", is_staff=True).exists())
        self.assertEqual(Ticket.objects.filter(title="VPN access is not working").count(), 1)
        self.assertEqual(
            Ticket.objects.filter(title="Production 500 on customer portal").count(),
            1,
        )
