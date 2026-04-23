from __future__ import annotations

import os

from celery import Celery

from .observability import setup_worker_tracing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

setup_worker_tracing()
