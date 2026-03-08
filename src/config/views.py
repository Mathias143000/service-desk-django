from __future__ import annotations

from django.conf import settings
from django.db import connections
from django.db.utils import DatabaseError
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


def database_is_available(alias: str = "default") -> bool:
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return False
    return True


class HealthCheckView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        database_ok = database_is_available()
        response_status = status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": "ok" if database_ok else "error",
                "database": "ok" if database_ok else "unavailable",
                "timestamp": timezone.now(),
                "version": settings.SPECTACULAR_SETTINGS["VERSION"],
            },
            status=response_status,
        )
