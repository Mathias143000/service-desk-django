from __future__ import annotations

from django.conf import settings
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_TRACING_INITIALIZED = False


def _setup_provider(*, service_name: str) -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces")
        )
    )
    trace.set_tracer_provider(provider)


def setup_django_tracing() -> None:
    global _TRACING_INITIALIZED
    if _TRACING_INITIALIZED or not settings.TRACING_ENABLED:
        return
    _setup_provider(service_name=settings.OTEL_SERVICE_NAME)
    DjangoInstrumentor().instrument()
    _TRACING_INITIALIZED = True


def setup_worker_tracing() -> None:
    global _TRACING_INITIALIZED
    if _TRACING_INITIALIZED or not settings.TRACING_ENABLED:
        return
    _setup_provider(service_name=settings.OTEL_SERVICE_NAME)
    _TRACING_INITIALIZED = True


def get_tracer(name: str):
    return trace.get_tracer(name)
