import calendar
from datetime import datetime

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.cache import cache

from config import celery_app
from .models import SustainabilityDashboard
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
