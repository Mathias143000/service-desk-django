from __future__ import annotations

import logging
import time

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from config.context import bind_request_id, clear_request_id
from config.metrics import (
    record_background_task,
    record_ticket_event,
    set_operational_snapshot,
    set_queue_depth,
)
from config.observability import get_tracer
from config.runtime import get_celery_queue_depth, set_runtime_snapshot

from .models import Ticket
from .reporting import build_ticket_analytics, build_ticket_summary

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


@shared_task(name="tickets.send_ticket_notification_stub")
def send_ticket_notification_stub(
    ticket_id: int,
    action: str,
    request_id: str | None = None,
) -> dict:
    started = time.perf_counter()
    token = bind_request_id(request_id or "background-task")
    try:
        with tracer.start_as_current_span("send_ticket_notification_stub") as span:
            span.set_attribute("ticket.id", ticket_id)
            span.set_attribute("ticket.action", action)
            ticket = Ticket.objects.get(id=ticket_id)
            ticket.notification_stub_sent_at = timezone.now()
            ticket.notification_stub_action = action
            ticket.save(update_fields=["notification_stub_sent_at", "notification_stub_action"])
            cache.set(
                f"service_desk:last_notification:{ticket_id}",
                {
                    "ticket_id": ticket_id,
                    "action": action,
                    "sent_at": ticket.notification_stub_sent_at.isoformat(),
                },
                timeout=settings.CACHE_TIMEOUT_SECONDS,
            )
            logger.info(
                "Notification stub sent for ticket %s",
                ticket_id,
                extra={"ticket_id": ticket_id, "action": action},
            )
            record_background_task("notification_stub", "success", time.perf_counter() - started)
            record_ticket_event("notification_stub_sent")
            return {"status": "sent", "ticket_id": ticket_id, "action": action}
    except Ticket.DoesNotExist:
        logger.warning("Ticket %s disappeared before notification task execution", ticket_id)
        record_background_task("notification_stub", "missing_ticket", time.perf_counter() - started)
        return {"status": "missing_ticket", "ticket_id": ticket_id}
    except Exception:
        logger.exception("Notification stub failed for ticket %s", ticket_id)
        record_background_task("notification_stub", "failed", time.perf_counter() - started)
        raise
    finally:
        clear_request_id(token)


@shared_task(name="tickets.refresh_operational_snapshot")
def refresh_operational_snapshot() -> dict:
    started = time.perf_counter()
    token = bind_request_id("beat-snapshot")
    try:
        with tracer.start_as_current_span("refresh_operational_snapshot"):
            queryset = Ticket.objects.select_related("created_by", "assigned_to")
            summary = build_ticket_summary(queryset)
            analytics = build_ticket_analytics(queryset)
            queue_depth = get_celery_queue_depth()
            payload = {
                "generated_at": timezone.now().isoformat(),
                "summary": summary,
                "analytics": analytics,
                "queue_depth": queue_depth,
            }
            set_runtime_snapshot(payload)
            set_queue_depth(settings.CELERY_TASK_DEFAULT_QUEUE, queue_depth)
            set_operational_snapshot(
                active_tickets=summary["active_tickets"],
                overdue_tickets=summary["overdue_tickets"],
            )
            logger.info("Operational snapshot refreshed")
            record_background_task(
                "refresh_operational_snapshot",
                "success",
                time.perf_counter() - started,
            )
            return payload
    except Exception:
        logger.exception("Operational snapshot refresh failed")
        record_background_task(
            "refresh_operational_snapshot",
            "failed",
            time.perf_counter() - started,
        )
        raise
    finally:
        clear_request_id(token)
