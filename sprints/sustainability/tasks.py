import calendar
from datetime import datetime
from string import Template
from typing import (
    Callable,
    Dict,
)

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import models

from config import celery_app
from .models import (
    Account,
    Cell,
    SustainabilityDashboard,
)
from .utils import generate_month_range


@celery_app.task()
def validate_worklog_cache(long_term=True, force_regenerate=False) -> bool:
    """
    Validate worklog caches for all months in the specified range and regenerates them, if required.
    It uses `settings.CACHE_WORKLOG_REGENERATE_LOCK` lock to avoid race conditions during regenerating long term caches.

    :param long_term: if true then checks all worklogs from `settings.TEMPO_START_YEAR` until the end of current month.
           Otherwise checks only the last `settings.CACHE_WORKLOG_MUTABLE_MONTHS` mutable months.
    :param force_regenerate: If true, regenerates cache for each month in the specified range.
    """
    today = datetime.today()

    if not cache.add(
        settings.CACHE_WORKLOG_REGENERATE_LOCK, True, settings.CACHE_WORKLOG_REGENERATE_LOCK_TIMEOUT_SECONDS
    ):  # Cache regeneration is still running or has ended unsuccessfully.
        return False

    if long_term:
        # Validate cache for all one-month periods from the beginning of `settings.TEMPO_START_YEAR` to the present one.
        start_year = parse(str(settings.TEMPO_START_YEAR))
        start_date = start_year.replace(month=1, day=1)
        cache_timeout = settings.CACHE_WORKLOG_TIMEOUT_LONG_TERM
        end_date = (today - relativedelta(months=settings.CACHE_WORKLOG_MUTABLE_MONTHS))
        last_day_of_month = calendar.monthrange(end_date.year, end_date.month)[1]
        end_date = end_date.replace(day=last_day_of_month)
    else:
        # Validate cache only for the last `settings.CACHE_WORKLOG_MUTABLE_MONTHS` mutable months.
        start_date = (today - relativedelta(months=settings.CACHE_WORKLOG_MUTABLE_MONTHS - 1)).replace(day=1)
        cache_timeout = settings.CACHE_WORKLOG_TIMEOUT_SHORT_TERM
        last_day_of_month = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day_of_month)

    start_str = start_date.strftime(settings.JIRA_API_DATE_FORMAT)
    end_str = end_date.strftime(settings.JIRA_API_DATE_FORMAT)

    for month_start, month_end in generate_month_range(start_str, end_str):
        SustainabilityDashboard.fetch_accounts_chunk(
            str(month_start),
            str(month_end),
            cache_timeout=cache_timeout,
            force=force_regenerate,
        )

    cache.delete(settings.CACHE_WORKLOG_REGENERATE_LOCK)
    return True


@celery_app.task()
def send_email_alerts() -> bool:
    """
    Send email alerts to users that keep track of the sustainability and budgets.

    Email addresses can be specified via:
        - `NOTIFICATIONS_SUSTAINABILITY_EMAILS` env variable - this subscribes an email for ALL notifications,
        - `Cell`/`Account` models of Django admin - only for specific cells/accounts.

    Note: notifications for projects that are not added to `Cells` (e.g. via Django admin) will be skipped for brevity.
    """
    today = datetime.today()
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    start_date = today.replace(day=1)
    end_date = today.replace(day=last_day_of_month)
    start_str = start_date.strftime(settings.JIRA_API_DATE_FORMAT)
    end_str = end_date.strftime(settings.JIRA_API_DATE_FORMAT)
    dashboard = SustainabilityDashboard(start_str, end_str)

    # Send alerts for cells.
    max_percentage_ratio = settings.SUSTAINABILITY_MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO * 100
    _send_email_alert(
        dashboard.get_projects_sustainability(),
        lambda k, v: v >= max_percentage_ratio and Cell.objects.filter(name=k).exists(),  # Ignore non-set projects.
        "Cell sustainability problem.",
        Template(
            f"The '% non-billable cell' of $entity is currently $ratio. It should be lower than {max_percentage_ratio}."
        ),
        Cell,
    )

    # Send alerts for budgets.
    _send_email_alert(
        dashboard.get_accounts_remaining_time(),
        lambda _, v: v < 0,
        "Budget problem.",
        Template(
            f"There is currently $ratio hours left for $entity."
        ),
        Account,
    )

    return True


def _send_email_alert(
    budgets: Dict[str, float], condition: Callable, title: str, message: Template, model: models.Model
) -> None:
    """
    Helper method for sending emails for Cells or Accounts.
    """
    for key, value in budgets.items():
        if condition(key, value):
            emails = settings.NOTIFICATIONS_SUSTAINABILITY_EMAILS
            try:
                emails.extend(model.objects.get(name=key).alert_emails)
            except (model.DoesNotExist, AttributeError):  # Emails not defined in the DB.
                pass

            if emails:
                send_mail(
                    title,
                    message.substitute(entity=key, ratio=str(round(value, 2))),
                    settings.DEFAULT_FROM_EMAIL,
                    emails
                )
