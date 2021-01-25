from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DashboardConfig(AppConfig):
    name = "sprints.dashboard"
    verbose_name = _("Dashboard")

    def ready(self):
        try:
            import sprints.users.signals  # noqa F401
        except ImportError:
            pass
