import calendar
from datetime import datetime
from typing import (
    Dict,
    Generator,
    Iterable,
    List,
    Set,
    Tuple,
)

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.cache import cache
from jira import (
    JIRAError,
    Worklog,
)

from sprints.dashboard.libs.jira import (
    Account,
    chunks,
    connect_to_jira,
)


def split_accounts_into_categories(accounts: List[Account]) -> Dict[str, List[Account]]:
    """
    Converts `List[Account]` into the following format: `Dict[category: str, List[Account]]`.
    """
    result: Dict[str, List[Account]] = {}
    for account in accounts:
        try:
            category = getattr(account, 'category').key
        except AttributeError:
            category = ''

        result.setdefault(category, []).append(account)
    return result


def generate_month_range(start: str, end: str) -> Generator[Tuple[datetime, datetime], None, None]:
    """Generates months between `start` and `end` dates."""
    start_date = parse(start)
    end_date = parse(end)

    current_date = start_date.replace(day=1)  # First day of each month
    while current_date < end_date:
        last_day_of_month = calendar.monthrange(current_date.year, current_date.month)[1]
        last_date_of_month = current_date.replace(day=last_day_of_month)
        yield max(current_date, start_date), min(last_date_of_month, end_date)
        current_date += relativedelta(months=1)


def _get_cached_dicts_from_keys(keys: Iterable) -> Dict:
    """Helper function for retrieving aggregated cache results."""
    result: Dict = {}
    for key in keys:
        cached_chunk = cache.get(key, {})
        result.update(cached_chunk)

    return result


def cache_worklogs_and_issues(required_worklogs: Set[str], long_term: bool) -> Dict[str, Dict[str, str]]:
    """
    Workaround for missing Tempo API data. It retrieves `required_worklogs` and caches them along with issues.

    It's possible to regenerate long-term cache by specifying `long_term` argument.
    """
    # Determine whether we're be using long-term cache or short-term one. Set keys and timeout accordingly.
    worklogs_key = settings.CACHE_WORKLOGS_KEY_LONG_TERM if long_term else settings.CACHE_WORKLOGS_KEY
    issues_key = settings.CACHE_ISSUES_KEY_LONG_TERM if long_term else settings.CACHE_ISSUES_KEY
    timeout = settings.CACHE_WORKLOG_TIMEOUT_LONG_TERM if long_term else settings.CACHE_ISSUES_TIMEOUT_SHOT_TERM

    # Check if worklogs are missing from cache.
    required_issues: Set[str] = set()
    worklogs: Dict[str, Dict[str, str]] = _get_cached_dicts_from_keys(
        (settings.CACHE_WORKLOGS_KEY, settings.CACHE_WORKLOGS_KEY_LONG_TERM)
    ) if not long_term else {}

    if missing_worklogs := required_worklogs - worklogs.keys():
        with connect_to_jira() as conn:
            retrieved_worklogs: List[Worklog] = conn.worklog_list(list(missing_worklogs))  # type: ignore
            for worklog in retrieved_worklogs:
                required_issues.add(worklog.issueId)

        # Check if worklogs are missing from cache.
        issues: Dict[str, Dict[str, str]] = _get_cached_dicts_from_keys(
            (settings.CACHE_ISSUES_KEY, settings.CACHE_ISSUES_KEY_LONG_TERM)
        ) if not long_term else {}
        new_issues: Dict[str, Dict[str, str]] = {}

        if missing_issues := required_issues - issues.keys():
            with connect_to_jira() as conn:
                try:
                    retrieved_issues = conn.search_issues(
                        f'id in ({",".join(missing_issues)})',
                        fields='project', maxResults=0
                    )
                except JIRAError:
                    # We can notice this for long-term cache, as Jira has limits for the header size.
                    retrieved_issues = []
                    for chunk in chunks(list(missing_issues), 12):
                        retrieved_issues = conn.search_issues(f'id in ({",".join(chunk)})',
                                                              fields='project', maxResults=0)
            new_issues = {issue.id: {'key': issue.key, 'project': issue.fields.project.name}
                          for issue in retrieved_issues}

        new_worklogs = {worklog.id: issues.get(worklog.issueId, new_issues.get(worklog.issueId))
                        for worklog in retrieved_worklogs}

        # We retrieve cache second time to avoid race conditions.
        with cache.lock(settings.CACHE_ISSUES_LOCK):
            if new_issues:
                issues = cache.get(issues_key) or {}
                issues.update(new_issues)
                cache.set(issues_key, issues, timeout)

            worklogs = cache.get(worklogs_key) or {}
            worklogs.update(new_worklogs)
            cache.set(worklogs_key, worklogs, timeout)

    return worklogs


def on_error(e: BaseException):
    """Callback method for retrieving exceptions from async processes."""
    raise e
