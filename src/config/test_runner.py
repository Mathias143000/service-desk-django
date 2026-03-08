from __future__ import annotations

from django.apps import apps
from django.test.runner import DiscoverRunner


class AppAwareDiscoverRunner(DiscoverRunner):
    """Run tests from installed apps when no explicit labels are provided."""

    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        labels = list(test_labels or [])
        if not labels:
            labels = [app_config.name for app_config in apps.get_app_configs()]
        return super().build_suite(test_labels=labels, extra_tests=extra_tests, **kwargs)
