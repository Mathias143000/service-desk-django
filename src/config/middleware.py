from __future__ import annotations

import logging
import time
import uuid

from django.conf import settings

from .context import bind_request_id, clear_request_id
from .metrics import record_http_request

logger = logging.getLogger(__name__)


class RequestObservabilityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get(settings.REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.request_id = request_id
        token = bind_request_id(request_id)
        started = time.perf_counter()
        logger.info("HTTP %s %s started", request.method, request.path)
        try:
            response = self.get_response(request)
            status_code = response.status_code
            response[settings.REQUEST_ID_HEADER] = request_id
            logger.info("HTTP %s %s -> %s", request.method, request.path, status_code)
            return response
        except Exception:
            status_code = 500
            logger.exception("Unhandled request failure for %s %s", request.method, request.path)
            raise
        finally:
            record_http_request(
                request.method,
                request.path,
                status_code,
                time.perf_counter() - started,
            )
            clear_request_id(token)
