from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WebhooksConfig(AppConfig):
    name = 'sprints.webhooks'
    verbose_name = _("Webhooks")

    def ready(self):
        try:
            import sprints.users.signals  # noqa F401
        except ImportError:
            pass
