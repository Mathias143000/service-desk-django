from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.db.utils import DatabaseError


def database_is_available(alias: str = "default") -> bool:
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return False
    return True


def redis_is_enabled() -> bool:
    return bool(settings.REDIS_URL)


def get_redis_client():
    if not redis_is_enabled():
        return None
    from redis import Redis

    return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)


def redis_is_available() -> bool | None:
    client = get_redis_client()
    if client is None:
        return None
    try:
        return bool(client.ping())
    except Exception:
        return False


def get_celery_queue_depth() -> int | None:
    client = get_redis_client()
    if client is None:
        return None
    try:
        return int(client.llen(settings.CELERY_TASK_DEFAULT_QUEUE))
    except Exception:
        return None


def get_runtime_snapshot() -> dict[str, Any] | None:
    return cache.get(settings.OPERATIONS_SNAPSHOT_CACHE_KEY)


def set_runtime_snapshot(payload: dict[str, Any]) -> None:
    cache.set(
        settings.OPERATIONS_SNAPSHOT_CACHE_KEY,
        payload,
        timeout=settings.CACHE_TIMEOUT_SECONDS,
    )
