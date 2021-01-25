from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import perform_login
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.translation import ugettext_lazy as _

from config.settings.base import (
    ACCOUNT_ALLOWED_EMAIL_DOMAINS,
    FRONTEND_URL,
)


class AccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        """This ensures that the provided domain is specified in the `ACCOUNT_ALLOWED_EMAIL_DOMAINS`."""
        domain = email.split("@")[-1]
        if domain not in ACCOUNT_ALLOWED_EMAIL_DOMAINS:
            raise ValidationError(
                _("Registration from this email domain is not allowed.")
            )
        return email

    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Constructs the email confirmation (activation) url.

        Note that if you have architected your system such that email
        confirmations are sent outside of the request context `request`
        can be `None` here.
        """
        url = f"{FRONTEND_URL}/verify-email/{emailconfirmation.key}"
        return url


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "SOCIALACCOUNT_ALLOW_REGISTRATION", True)

    def pre_social_login(self, request, sociallogin):
        """Add social account to an existing account (if registered with email and password)."""
        social_user = sociallogin.user
        if social_user.id:
            return

        # noinspection PyPep8Naming
        User = get_user_model()
        try:
            user = User.objects.get(email=social_user.email)
            sociallogin.state["process"] = "connect"
            perform_login(request, user, "none")
        except User.DoesNotExist:
            pass
