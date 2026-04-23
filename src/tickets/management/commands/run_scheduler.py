from __future__ import annotations

import logging
import signal
import time
from threading import Event

from django.conf import settings
from django.core.management.base import BaseCommand

from tickets.tasks import refresh_operational_snapshot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the periodic scheduler loop for operational snapshots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=settings.CELERY_OPERATIONS_SNAPSHOT_INTERVAL_SECONDS,
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Execute a single snapshot refresh and exit.",
        )

    def handle(self, *args, **options):
        interval = max(1, options["interval"])
        run_once = options["once"]
        stop_event = Event()

        def request_stop(signum, _frame):
            logger.info("Scheduler loop received signal %s, shutting down", signum)
            stop_event.set()

        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, request_stop)

        logger.info("Scheduler loop started with interval=%s seconds", interval)
        while not stop_event.is_set():
            started = time.monotonic()
            try:
                refresh_operational_snapshot.apply(throw=True)
                logger.info("Operational snapshot cycle completed")
            except Exception:
                logger.exception("Operational snapshot cycle failed")
            if run_once:
                break

            elapsed = time.monotonic() - started
            sleep_for = max(0.0, interval - elapsed)
            stop_event.wait(timeout=sleep_for)

        logger.info("Scheduler loop stopped")
