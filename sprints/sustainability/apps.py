from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SustainabilityConfig(AppConfig):
    name = 'sprints.sustainability'
    verbose_name = _("Sustainability")

    def ready(self):
        try:
            import sprints.users.signals  # noqa F401
        except ImportError:
            pass
