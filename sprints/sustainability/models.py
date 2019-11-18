import calendar
from datetime import (
    datetime,
    timedelta,
)
from multiprocessing.pool import ThreadPool
from typing import (
    Dict,
    List,
    Union,
)

from dateutil.parser import parse
from django.conf import settings
from django.core.cache import cache
from django.db import models
from jira.resources import PropertyHolder

from sprints.dashboard.libs.jira import connect_to_jira
from sprints.dashboard.utils import get_current_sprint_end_date
from sprints.sustainability.utils import (
    generate_month_range,
    on_error,
)


class SustainabilityAccount:
    """
    Aggregates account name and key along with:
        - overall time spent on the account,
        - person-specific time spent on the account.
    """

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.overall: float = 0
        self.by_person: Dict[str, float] = {}

    def __add__(self, other):
        result = SustainabilityAccount(self.name)
        result.overall = self.overall + other.overall
        result.by_person = {
            key: self.by_person.get(key, 0) + other.by_person.get(key, 0)
            for key in set(self.by_person) | set(other.by_person)
        }
        return result

    def __radd__(self, other):
        return self

    def add_reports(self, reports: List[PropertyHolder]) -> None:
        """Converts reports with worklogs into overall hours."""
        for report in reports:
            hours = report.hours
            username = report.user.displayName

            self.overall += hours
            self.by_person[username] = self.by_person.get(username, 0) + hours

    def calculate_budgets(self, start_date: datetime, end_date: datetime) -> None:
        """
        Calculates budgets for the account.
        Retrieves account's budgets from the DB.
        """
        year = start_date.year
        now = datetime.now()
        present_month = now.month if now.year == year else 13  # Hack for checking previous years.
        present_day = now.day
        budgets = Budget.objects.filter(name=self.name).order_by('date')
        self.budgets: List[int] = []
        self.ytd_goal = 0.

        current_month = 1
        current_budget = 0
        # Calculate budgets provided in the DB.
        for budget in budgets:
            if budget.date.year != year:
                current_budget = budget.hours

            else:
                previous_month = current_month
                previous_budget = current_budget
                current_month = budget.date.month
                current_budget = budget.hours
                for month in range(previous_month, current_month):
                    self._process_budget(year, month, present_month, previous_budget)

        # Calculate remaining budgets.
        for month in range(len(self.budgets) + 1, 13):
            self._process_budget(year, month, present_month, current_budget)

        # Calculate available budget for the next sprint.
        daily_budget: Dict[int, float] = {
            now.month: self.calculate_workday_budget(year, now.month, self.budgets[now.month - 1]),
            now.month + 1: self.calculate_workday_budget(year, now.month + 1, self.budgets[now.month]),
        }
        self.next_sprint_goal = self.ytd_goal + self._calculate_partial_budget_for_workdays(now, end_date, daily_budget)

    def _process_budget(self, year, month, present_month, budget) -> None:
        """Processes monthly budget (full or partial)."""
        if month < present_month:
            self.ytd_goal += budget
        elif month == present_month:
            # Calculate partial budget for the current month.
            now = datetime.now()
            start = now.replace(day=1)
            daily_budget = {now.month: self.calculate_workday_budget(year, now.month, budget)}

            self.ytd_goal += self._calculate_partial_budget_for_workdays(start, now, daily_budget)

        self.budgets.append(budget)

    @staticmethod
    def _calculate_partial_budget_for_workdays(start: datetime, end: datetime, daily_budget: Dict[int, float]) -> float:
        """
        Calculates budget for the workdays from `start` to `end` using the `daily_budget` per workday.
        """
        partial_budget = 0.
        for n in range(int((end - start).days)):
            date = (start + timedelta(n))
            if date.weekday() < 5:  # Do not count weekends.
                partial_budget += daily_budget[date.month]

        return partial_budget

    @staticmethod
    def calculate_workday_budget(year: int, month: int, monthly_budget: int) -> float:
        """
        Returns daily budget basing only on the working days.
        Useful for precise estimations for the sprint planning.
        """
        cal = calendar.Calendar()
        working_days = len([x for x in cal.itermonthdays2(year, month) if x[0] != 0 and x[1] < 5])
        return monthly_budget / working_days


class SustainabilityDashboard:
    """
    Aggregates accounts into a single dashboard.
    """

    def __init__(self, from_: str, to: str, budgets: bool = False) -> None:
        self.generate_budgets = budgets
        self.from_ = from_
        self.to = to

        self.billable_accounts: Union[List[SustainabilityAccount], Dict[str, SustainabilityAccount]] = {}
        self.non_billable_accounts: Union[List[SustainabilityAccount], Dict[str, SustainabilityAccount]] = {}
        self.non_billable_responsible_accounts: \
            Union[List[SustainabilityAccount], Dict[str, SustainabilityAccount]] = {}

        self.fetch_accounts()

    def fetch_accounts(self):
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
                for args in generate_month_range(self.from_, self.to)
            ]
            output = [p.get(settings.MULTIPROCESSING_TIMEOUT) for p in results]

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

            if self.generate_budgets:
                end_date = get_current_sprint_end_date('future')

                accounts = getattr(self, category)
                for account in accounts:
                    account.calculate_budgets(parse(self.from_), parse(end_date))

    @staticmethod
    def fetch_accounts_chunk(from_: str, to: str, cache_timeout=0, force=False) -> Dict[str, Dict]:
        """Wraps fetching account chunks for caching."""
        key = f"{settings.CACHE_SUSTAINABILITY_PREFIX}{from_} - {to}"
        if force:
            cache.set(key, categories := SustainabilityDashboard._fetch_accounts_chunk(from_, to), cache_timeout)
            return categories

        if not (categories := cache.get(key)):
            categories = cache.get_or_set(key, SustainabilityDashboard._fetch_accounts_chunk(from_, to), cache_timeout)
        return categories

    @staticmethod
    def _fetch_accounts_chunk(from_: str, to: str) -> Dict[str, Dict]:
        """Fetches worklogs by a month, which is much faster."""
        with connect_to_jira() as conn:
            reports = conn.report(from_, to)
        categories: Dict[str, Dict[str, SustainabilityAccount]] = {}
        for weekly_report in reports.reports:
            for account_type in weekly_report.reports:
                for account_category in account_type.reports:
                    category = categories.setdefault(account_category.name, {})
                    for account_reports in account_category.reports:
                        account = category.setdefault(
                            account_reports.name,
                            SustainabilityAccount(account_reports.name),
                        )
                        account.add_reports(account_reports.reports)

        return categories


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
