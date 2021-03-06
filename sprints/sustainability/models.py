import calendar
import datetime
from collections import defaultdict
from multiprocessing.pool import ThreadPool
from typing import (
    Dict,
    List,
    Set,
    Union,
)

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models
from jira.resources import PropertyHolder
from more_itertools import pairwise

from sprints.dashboard.libs.jira import connect_to_jira
from sprints.dashboard.utils import get_current_sprint_end_date
from sprints.sustainability.utils import (
    cache_worklogs_and_issues,
    diff_month,
    generate_month_range,
    on_error,
)


class Budget(models.Model):
    """
    Stores monthly budgets for accounts.
    If the budget for the specific month is not present, the last existing one is used.
    """

    name = models.CharField(max_length=255, help_text="Account's name.")
    date = models.DateField(
        help_text="Year and month of the budget. If not specified, the last month's budget is applied."
    )
    hours = models.IntegerField(help_text="Number of available hours for this month.")

    def __str__(self):
        return f"{self.name}: {self.date.strftime('%Y-%m')}"


class Account(models.Model):
    """
    Stores email addresses for sending notifications about problems with the budgets of the account.
    """

    name = models.CharField(max_length=255, help_text="Account's name.")
    alert_emails = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text="List of comma-separated (`,`) email addresses that will be periodically notified about budget "
                  "overhead.",
    )

    def __str__(self):
        return f"{self.name}"


class Cell(models.Model):
    """
    Stores email addresses for notifications about problems with the sustainability of the project.

    If the project is not added, notifications will not be sent for it.
    """

    name = models.CharField(max_length=255, help_text="Cell's name.")
    alert_emails = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text="List of comma-separated (`,`) email addresses that will be periodically notified about cell "
                  "sustainability problems.",
    )

    def __str__(self):
        return f"{self.name}"


class SustainabilityAccount:
    """
    Aggregates account name and key along with:
        - overall time spent on the account,
        - project-specific time spent on the account.
        - person-specific time spent on the account.
    """

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.overall: float = 0
        self.by_project: Dict[str, float] = {}
        self.by_person: Dict[str, float] = {}
        self.ytd_overall: float = 0
        self.ytd_by_project: Dict[str, float] = {}
        self.ytd_by_person: Dict[str, float] = {}
        self.budgets: Dict[str, int] = {}

    def __add__(self, other):
        result = SustainabilityAccount(self.name)
        result.overall = self.overall + other.overall
        result.by_project = {
            key: self.by_project.get(key, 0) + other.by_project.get(key, 0)
            for key in set(self.by_project) | set(other.by_project)
        }
        result.by_person = {
            key: self.by_person.get(key, 0) + other.by_person.get(key, 0)
            for key in set(self.by_person) | set(other.by_person)
        }
        return result

    def __radd__(self, other):
        return self

    def add_reports(self, reports: List[PropertyHolder], worklogs: Dict[str, Dict[str, str]]) -> None:
        """Converts reports with worklogs into overall hours."""
        for report in reports:
            hours = report.hours
            username = report.user.displayName
            worklog_id = str(report.typeId)
            project = worklogs[worklog_id]['project']

            self.overall += hours
            self.by_project[project] = self.by_project.get(project, 0) + hours
            self.by_person[username] = self.by_person.get(username, 0) + hours

    def calculate_budgets(
        self, ytd_start: datetime.date, start: datetime.date, end_sprint: datetime.date, end: datetime.date
    ) -> None:
        """
        Calculates budgets for the account.
        Retrieves account's budgets from the DB.
        """

        self.budgets = {}  # TODO: remove later. For now we need to do this to avoid dealing with cache invalidation.
        budgets = list(Budget.objects.filter(name=self.name).order_by('date'))
        self.next_sprint_goal = self._calculate_budgets(ytd_start, end_sprint, budgets)
        self.ytd_goal = self._calculate_budgets(ytd_start, datetime.date.today(), budgets)
        self.period_goal = self._calculate_budgets(start, end, budgets)

    def _calculate_budgets(self, start_date: datetime.date, end_date: datetime.date, budgets: List[Budget]) -> float:
        """
        Inner method for calculating budgets for the account.

        It uses `pairwise` to process chronological pairs of existing budgets.
        The list of budgets is extended by `None` to have a clear indication which budget is the last one.
        """
        goal = 0.
        current_start = start_date  # Local range

        start_budget: Budget
        end_budget: Union[Budget, None]
        # noinspection PyTypeChecker
        for start_budget, end_budget in pairwise(budgets + [None]):  # type: ignore
            current_start = max(current_start, start_budget.date)
            current_end = end_date
            if end_budget:
                current_end = min(current_end, end_budget.date + relativedelta(months=-1, day=31))

            if current_start <= current_end:
                goal += self._calculate_budget(current_start, current_end, start_budget.hours)
                self._add_budget(start_budget, current_start, current_end)
                current_start = current_end

        return goal

    @classmethod
    def _calculate_budget(cls, start: datetime.date, end: datetime.date, hours: int) -> float:
        """Processes monthly budget (full or partial)."""
        end_last_day_of_month = calendar.monthrange(end.year, end.month)[1]
        partial_hours = 0.

        # First edge case - the start day is not the first day of the month.
        if start.day != 1:
            partial_end = min(start + relativedelta(day=31), end)  # Partial end cannot exceed the real end.
            partial_hours += cls._calculate_partial_budget(start, partial_end, hours)
            start = start + relativedelta(months=+1, day=1)

        # Second edge case - the end day is not the last day of the month.
        # If calculated during the first edge case, do not calculate it again.
        if end.day != end_last_day_of_month and start <= end:
            partial_start = end.replace(day=1)
            partial_hours += cls._calculate_partial_budget(partial_start, end, hours)
            end = end + relativedelta(months=-1, day=31)

        monthly_hours = diff_month(start, end) * hours if start <= end else 0  # Calculate months between edge cases.
        return monthly_hours + partial_hours

    @classmethod
    def _calculate_partial_budget(cls, start: datetime.date, end: datetime.date, hours: int) -> float:
        """Calculate budget for a part of one month."""
        if start.month != end.month:
            raise AttributeError("`start` and `end` must be in the same month.")

        days_in_month = calendar.monthrange(start.year, start.month)[1]
        return hours / days_in_month * ((end - start).days + 1)

    def _add_budget(self, budget: Budget, start: datetime.date, end: datetime.date) -> None:
        """
        Add each month of the processed budget to the list. The end result is a per-month list of budget hours.
        """
        for month, _ in generate_month_range(str(start), str(end)):
            self.budgets[month.strftime('%B %Y')] = budget.hours


class SustainabilityDashboard:
    """
    Aggregates accounts into a single dashboard.
    """

    def __init__(self, from_: str, to: str, budgets: bool = False) -> None:
        self.generate_budgets = budgets
        self.from_ = from_
        self.to = to

        self.ytd_from = parse(from_).replace(month=1, day=1).strftime(settings.JIRA_API_DATE_FORMAT)
        today = datetime.datetime.today()
        last_day_of_month = calendar.monthrange(today.year, today.month)[1]
        current_end_date = today.replace(day=last_day_of_month)
        self.ytd_to = min(current_end_date, parse(to).replace(month=12, day=31)).strftime(settings.JIRA_API_DATE_FORMAT)

        self.billable_accounts: Union[List[SustainabilityAccount], Dict[str, SustainabilityAccount]] = {}
        self.non_billable_accounts: Union[List[SustainabilityAccount], Dict[str, SustainabilityAccount]] = {}
        self.non_billable_responsible_accounts: \
            Union[List[SustainabilityAccount], Dict[str, SustainabilityAccount]] = {}

        self.fetch_accounts(self.from_, self.to)
        self.fetch_accounts(self.ytd_from, self.ytd_to, generate_ytd=True)

    def fetch_accounts(self, from_: str, to: str, generate_ytd: bool = False) -> None:
        """
        Fetches aggregated worklogs in an async way.
        FIXME: The exceptions here are logged, but they are not being captured by `p.get()` for some reason.
        """
        with ThreadPool(processes=settings.MULTIPROCESSING_POOL_SIZE) as pool:
            results = [pool.apply_async(
                self.fetch_accounts_chunk,
                args + (settings.CACHE_WORKLOG_TIMEOUT_ONE_TIME,),
                error_callback=on_error,
            )
                for args in generate_month_range(from_, to)
            ]
            output = [p.get(settings.MULTIPROCESSING_TIMEOUT) for p in results]

        # Calculate desired range.
        if not generate_ytd:
            for chunk in output:
                for category, accounts in chunk.items():
                    try:
                        result_accounts = getattr(self, settings.TEMPO_ACCOUNT_TRANSLATE[category])
                        for account_name, account in accounts.items():
                            result_accounts[account_name] = result_accounts.get(account_name, None) + account
                    except KeyError:
                        # Ignore non-existing categories
                        pass

            for category in settings.TEMPO_ACCOUNT_TRANSLATE.values():
                setattr(self, category, getattr(self, category).values())

                end_sprint_date = get_current_sprint_end_date('future')

                accounts = getattr(self, category)
                for account in accounts:
                    args = map(lambda d: parse(d).date(), [self.ytd_from, from_, end_sprint_date, to])
                    account.calculate_budgets(*args)

        # Generate year-to-date values.
        else:
            ytd_results: Dict[str, SustainabilityAccount] = {}
            for chunk in output:
                for accounts in chunk.values():
                    for account_name, account in accounts.items():
                        ytd_results[account_name] = ytd_results.get(account_name, None) + account

            for category in settings.TEMPO_ACCOUNT_TRANSLATE.values():
                for account in getattr(self, category):
                    ytd_account = ytd_results.get(account.name)
                    if ytd_account:
                        account.ytd_overall = ytd_account.overall
                        account.ytd_by_project = ytd_account.by_project
                        account.ytd_by_person = ytd_account.by_person

    @staticmethod
    def fetch_accounts_chunk(from_: str, to: str, cache_timeout=0, force=False) -> Dict[str, Dict]:
        """Wraps fetching account chunks for caching."""
        key = f"{settings.CACHE_SUSTAINABILITY_PREFIX}{from_} - {to}"
        if force:
            cache.set(
                key,
                categories := SustainabilityDashboard._fetch_accounts_chunk(from_, to, force),
                cache_timeout
            )
            return categories

        if not (categories := cache.get(key)):
            categories = cache.get_or_set(
                key,
                SustainabilityDashboard._fetch_accounts_chunk(from_, to, force),
                cache_timeout
            )
        return categories

    @staticmethod
    def _fetch_accounts_chunk(from_: str, to: str, force_regenerate_worklogs=False) -> Dict[str, Dict]:
        """Fetches worklogs by a month, which is much faster."""
        with connect_to_jira() as conn:
            reports = conn.report(from_, to)
        categories: Dict[str, Dict[str, SustainabilityAccount]] = {}
        # HACK: Ugly workaround, because Tempo team utilization report doesn't provide neither ticket's key nor its ID.
        worklog_ids: Set[str] = set()
        for weekly_report in reports.reports:
            for account_type in weekly_report.reports:
                for account_category in account_type.reports:
                    for account_reports in account_category.reports:
                        for report in account_reports.reports:
                            worklog_ids.add(str(report.typeId))

        worklogs = cache_worklogs_and_issues(worklog_ids, force_regenerate_worklogs)

        for weekly_report in reports.reports:
            for account_type in weekly_report.reports:
                for account_category in account_type.reports:
                    category = categories.setdefault(account_category.name, {})
                    for account_reports in account_category.reports:
                        account = category.setdefault(
                            account_reports.name,
                            SustainabilityAccount(account_reports.name),
                        )
                        account.add_reports(account_reports.reports, worklogs)

        return categories

    def get_projects_sustainability(self) -> Dict[str, float]:
        """Retrieve sustainability of all processed projects."""
        aggregated_projects: Dict[str, Dict[str, float]] = {}
        for category in settings.TEMPO_ACCOUNT_TRANSLATE.values():
            for account in getattr(self, category):
                for project, hours in account.by_project.items():
                    aggregated_projects.setdefault(project, defaultdict(float))
                    aggregated_projects[project][category] += hours

        sustainability: Dict[str, float] = {}
        for project, data in aggregated_projects.items():
            billable_hours = data[settings.TEMPO_ACCOUNT_TRANSLATE[settings.TEMPO_BILLABLE_ACCOUNT_NAME]]
            non_billable_reponsible_hours = \
                data[settings.TEMPO_ACCOUNT_TRANSLATE[settings.TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT_NAME]]
            cell_hours = billable_hours + non_billable_reponsible_hours
            try:
                responsible_hours = non_billable_reponsible_hours / cell_hours * 100
            except ZeroDivisionError:
                responsible_hours = float('inf')
            sustainability[project] = responsible_hours

        return sustainability

    def get_accounts_remaining_time(self) -> Dict[str, float]:
        """Retrieve time left of all fetched accounts."""
        accounts: Dict[str, float] = defaultdict(float)
        for category in settings.TEMPO_ACCOUNT_TRANSLATE.values():
            for account in getattr(self, category):
                accounts[account.name] += account.ytd_goal - account.ytd_overall

        return accounts
