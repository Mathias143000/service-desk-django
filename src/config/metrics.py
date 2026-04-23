from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUESTS_TOTAL = Counter(
    "service_desk_http_requests_total",
    "HTTP requests handled by the service desk API",
    labelnames=("method", "path", "status"),
)
REQUEST_LATENCY = Histogram(
    "service_desk_http_request_duration_seconds",
    "Request latency for the service desk API",
    labelnames=("method", "path"),
)
TICKET_EVENTS_TOTAL = Counter(
    "service_desk_ticket_events_total",
    "Ticket-related business events",
    labelnames=("kind",),
)
BACKGROUND_TASKS_TOTAL = Counter(
    "service_desk_background_tasks_total",
    "Background task executions",
    labelnames=("task_name", "status"),
)
BACKGROUND_TASK_DURATION = Histogram(
    "service_desk_background_task_duration_seconds",
    "Background task latency",
    labelnames=("task_name",),
)
DEPENDENCY_UP = Gauge(
    "service_desk_dependency_up",
    "Dependency availability for the service desk stand",
    labelnames=("dependency",),
)
QUEUE_DEPTH = Gauge(
    "service_desk_queue_depth",
    "Approximate Celery queue depth",
    labelnames=("queue",),
)
OVERDUE_TICKETS = Gauge(
    "service_desk_overdue_tickets",
    "Current overdue ticket count from the latest operational snapshot",
)
ACTIVE_TICKETS = Gauge(
    "service_desk_active_tickets",
    "Current active ticket count from the latest operational snapshot",
)


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    REQUESTS_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(duration_seconds)


def record_ticket_event(kind: str) -> None:
    TICKET_EVENTS_TOTAL.labels(kind=kind).inc()


def record_background_task(task_name: str, status: str, duration_seconds: float) -> None:
    BACKGROUND_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()
    BACKGROUND_TASK_DURATION.labels(task_name=task_name).observe(duration_seconds)


def set_dependency_state(dependency: str, available: bool | None) -> None:
    if available is None:
        return
    DEPENDENCY_UP.labels(dependency=dependency).set(1 if available else 0)


def set_queue_depth(queue_name: str, depth: int | None) -> None:
    if depth is None:
        return
    QUEUE_DEPTH.labels(queue=queue_name).set(depth)


def set_operational_snapshot(*, active_tickets: int, overdue_tickets: int) -> None:
    ACTIVE_TICKETS.set(active_tickets)
    OVERDUE_TICKETS.set(overdue_tickets)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
