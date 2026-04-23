from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from .logging import build_logging_config

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name, "1" if default else "0")
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "dev-secret-key-change-me-please-at-least-32-characters",
)
DEBUG = env_bool("DJANGO_DEBUG", False)
APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
REQUEST_ID_HEADER = os.getenv("REQUEST_ID_HEADER", "X-Request-ID")
JSON_LOGS = env_bool("JSON_LOGS", not DEBUG)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")
USE_X_FORWARDED_HOST = env_bool("DJANGO_USE_X_FORWARDED_HOST", True)

TRACING_ENABLED = env_bool("TRACING_ENABLED", False)
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "service-desk-api")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", REDIS_URL)
ASYNC_TASKS_ENABLED = env_bool("ASYNC_TASKS_ENABLED", bool(REDIS_URL))
CACHE_TIMEOUT_SECONDS = int(os.getenv("CACHE_TIMEOUT_SECONDS", "300"))
OPERATIONS_SNAPSHOT_CACHE_KEY = "service_desk:operations_snapshot"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "tickets",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.RequestObservabilityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


if os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "60")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TEST_RUNNER = "config.test_runner.AppAwareDiscoverRunner"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("PAGE_SIZE", "20")),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

TICKET_SLA_HOURS = {
    "low": int(os.getenv("TICKET_SLA_LOW_HOURS", "72")),
    "medium": int(os.getenv("TICKET_SLA_MEDIUM_HOURS", "24")),
    "high": int(os.getenv("TICKET_SLA_HIGH_HOURS", "8")),
    "critical": int(os.getenv("TICKET_SLA_CRITICAL_HOURS", "4")),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Service Desk API",
    "DESCRIPTION": "Ticketing API with JWT auth, role-based access, and audit log.",
    "VERSION": APP_VERSION,
}

LOGGING = build_logging_config(service_name=OTEL_SERVICE_NAME, json_logs=JSON_LOGS)

if REDIS_CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_CACHE_URL,
            "TIMEOUT": CACHE_TIMEOUT_SECONDS,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "service-desk-cache",
            "TIMEOUT": CACHE_TIMEOUT_SECONDS,
        }
    }

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_DEFAULT_QUEUE = os.getenv("CELERY_TASK_DEFAULT_QUEUE", "service-desk")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = env_bool("CELERY_TASK_EAGER_PROPAGATES", True)
CELERY_TASK_ROUTES = {
    "tickets.send_ticket_notification_stub": {"queue": CELERY_TASK_DEFAULT_QUEUE},
    "tickets.refresh_operational_snapshot": {"queue": CELERY_TASK_DEFAULT_QUEUE},
}
CELERY_RESULT_EXPIRES = int(os.getenv("CELERY_RESULT_EXPIRES_SECONDS", "3600"))
CELERY_OPERATIONS_SNAPSHOT_INTERVAL_SECONDS = int(
    os.getenv("CELERY_OPERATIONS_SNAPSHOT_INTERVAL_SECONDS", "30")
)
CELERY_BEAT_SCHEDULE = {
    "refresh-operational-snapshot": {
        "task": "tickets.tasks.refresh_operational_snapshot",
        "schedule": timedelta(seconds=CELERY_OPERATIONS_SNAPSHOT_INTERVAL_SECONDS),
        "options": {
            "queue": CELERY_TASK_DEFAULT_QUEUE,
            "routing_key": CELERY_TASK_DEFAULT_QUEUE,
        },
    }
}

if not DEBUG:
    enable_ssl = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
    SECURE_SSL_REDIRECT = enable_ssl
    SESSION_COOKIE_SECURE = enable_ssl
    CSRF_COOKIE_SECURE = enable_ssl
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"

    if env_bool("DJANGO_TRUST_X_FORWARDED_PROTO", True):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    if enable_ssl:
        SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
        SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
            "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
            True,
        )
        SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", True)
