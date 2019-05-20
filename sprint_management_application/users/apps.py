from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "sprint_management_application.users"
    verbose_name = _("Users")

    def ready(self):
        try:
            import sprint_management_application.users.signals  # noqa F401
        except ImportError:
            pass
