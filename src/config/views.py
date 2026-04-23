from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .metrics import (
    render_metrics,
    set_dependency_state,
    set_operational_snapshot,
    set_queue_depth,
)
from .runtime import (
    database_is_available,
    get_celery_queue_depth,
    get_runtime_snapshot,
    redis_is_available,
    redis_is_enabled,
)


class HealthCheckView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        database_ok = database_is_available()
        redis_ok = redis_is_available()
        queue_depth = get_celery_queue_depth()

        set_dependency_state("database", database_ok)
        set_dependency_state("redis", redis_ok)
        set_queue_depth(settings.CELERY_TASK_DEFAULT_QUEUE, queue_depth)

        dependencies_ok = database_ok and (redis_ok in (True, None))
        response_status = (
            status.HTTP_200_OK
            if dependencies_ok
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(
            {
                "status": "ok" if dependencies_ok else "error",
                "database": "ok" if database_ok else "unavailable",
                "redis": (
                    "disabled"
                    if not redis_is_enabled()
                    else ("ok" if redis_ok else "unavailable")
                ),
                "queue_depth": queue_depth,
                "timestamp": timezone.now(),
                "version": settings.APP_VERSION,
            },
            status=response_status,
        )


class ReadyView(HealthCheckView):
    pass


class LiveView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response({"status": "ok", "version": settings.APP_VERSION})


class MetricsView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        snapshot = get_runtime_snapshot()
        if snapshot:
            summary = snapshot.get("summary", {})
            set_operational_snapshot(
                active_tickets=summary.get("active_tickets", 0),
                overdue_tickets=summary.get("overdue_tickets", 0),
            )
            set_queue_depth(
                settings.CELERY_TASK_DEFAULT_QUEUE,
                snapshot.get("queue_depth"),
            )
        payload, content_type = render_metrics()
        return HttpResponse(payload, content_type=content_type)


class RuntimeStatusView(APIView):
    def get(self, request):
        queue_depth = get_celery_queue_depth()
        snapshot = get_runtime_snapshot()
        set_queue_depth(settings.CELERY_TASK_DEFAULT_QUEUE, queue_depth)
        return Response(
            {
                "queue_name": settings.CELERY_TASK_DEFAULT_QUEUE,
                "queue_depth": queue_depth,
                "runtime_snapshot": snapshot,
                "timestamp": timezone.now(),
            }
        )
