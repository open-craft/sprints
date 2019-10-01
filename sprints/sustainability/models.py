import calendar
import re
from datetime import (
    datetime,
    timedelta,
)
from multiprocessing.pool import Pool
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from dateutil.parser import parse
from django.conf import settings
from django.db import models

from sprints.dashboard.libs.jira import (
    Account,
    CustomJira,
    connect_to_jira,
)
from sprints.dashboard.utils import (
    get_all_sprints,
    get_cells,
    get_sprint_end_date,
    get_sprint_start_date,
)
from sprints.sustainability.utils import split_accounts_into_categories


class SustainabilityAccount:
    """
    Aggregates account name and key along with:
        - overall time spent on the account,
        - cell-specific time spent on the account,
        - person-specific time spent on the account.
    """

    def __init__(
        self,
        account: Dict[str, Union[str, int]],
        cell_names: Dict[str, str],
        from_: str,
        to: str,
        generate_budgets: bool = False,
        start_date_str: str = '',
        end_date_str: str = '',
    ) -> None:
        self.key = account['key']
        self.name = account['name']
        with connect_to_jira() as conn:
            expenses = conn.expenses(int(account['id']), from_, to)

        self.overall: float = getattr(expenses, 'hours', 0)
        self.by_cell: Dict[str, float] = {}
        self.by_person: Dict[str, float] = {}

        cell_hours: Dict[str, float] = {}
        for report in expenses.reports:
            issue_search = re.search(settings.SPRINT_ISSUE_REGEX, report.name)
            if issue_search:
                cell = issue_search.group(1)
                cell_hours[cell] = cell_hours.get(cell, 0) + report.hours

            for worklog in report.reports:
                username = worklog.user.displayName
                self.by_person[username] = self.by_person.get(username, 0) + worklog.hours

        # Translate cell keys into their names
        for cell, hours in cell_hours.items():
            try:
                self.by_cell[cell_names[cell]] = hours
            except KeyError:
                # We can safely ignore non-cell issues here.
                pass

        if generate_budgets:
            # Retrieve account's budgets from the DB.
            year = int(from_.split('-')[0])
            now = datetime.now()
            present_month = now.month if now.year == year else 13  # Hack for checking previous years.
            present_day = now.day
            budgets = Budget.objects.filter(name=self.key).order_by('date')
            self.budgets: List[int] = []
            self.ytd_goal = 0.

            current_month = 1
            current_budget = 0
            for budget in budgets:
                if budget.date.year != year:
                    current_budget = budget.hours

                else:
                    previous_month = current_month
                    previous_budget = current_budget
                    current_month = budget.date.month
                    current_budget = budget.hours
                    for month in range(previous_month, current_month):
                        if month < present_month:
                            self.ytd_goal += previous_budget
                        elif month == present_month:
                            # Calculate partial budget for the current month.
                            self.ytd_goal += \
                                self.calculate_daily_budget(year, present_month, previous_budget) * present_day
                        self.budgets.append(previous_budget)

            for month in range(len(self.budgets) + 1, 13):
                if month < present_month:
                    self.ytd_goal += current_budget
                elif month == present_month:
                    # Calculate partial budget for the current month.
                    self.ytd_goal += self.calculate_daily_budget(year, present_month, current_budget) * present_day

                self.budgets.append(current_budget)

            # Calculate available budget for the next sprint.
            start_date = parse(start_date_str)
            end_date = parse(end_date_str)
            partial_budgets: Dict[int, float] = {
                start_date.month:
                    self.calculate_workday_budget(year, start_date.month, self.budgets[start_date.month - 1]),
                end_date.month: self.calculate_workday_budget(year, end_date.month, self.budgets[end_date.month - 1]),
            }
            self.next_sprint_budget = 0.

            for n in range(int((end_date - start_date).days)):
                date = (start_date + timedelta(n))
                if date.weekday() < 5:  # Do not count weekends.
                    self.next_sprint_budget += partial_budgets[date.month]

    @staticmethod
    def calculate_daily_budget(year: int, month: int, monthly_budget: int) -> float:
        """
        Returns daily budget basing on the whole month.
        Useful for broad estimations for the whole month.
        """
        days_in_month = calendar.monthrange(year, month)[1]
        return monthly_budget / days_in_month

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

    def __init__(self, conn: CustomJira, from_: str, to: Optional[str]) -> None:
        self.jira_connection = conn
        self.from_ = from_
        self.to = to
        self.generate_budgets = False if self.to else True

        accounts: List[Account] = self.jira_connection.accounts()
        split_accounts = split_accounts_into_categories(accounts)
        cells = get_cells(self.jira_connection)
        self.cell_names = {cell.key: cell.name for cell in cells}

        if not self.generate_budgets:
            self.billable_accounts = self.generate_expenses(split_accounts[settings.TEMPO_BILLABLE_ACCOUNT])
            self.non_billable_accounts = self.generate_expenses(split_accounts[settings.TEMPO_NON_BILLABLE_ACCOUNT])
            self.non_billable_responsible_accounts = self.generate_expenses(
                split_accounts[settings.TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT])

        else:
            year = self.from_
            self.from_ = f'{year}-01-01'
            self.to = f'{year}-12-31'

            self.billable_accounts = self.generate_expenses(split_accounts[settings.TEMPO_BILLABLE_ACCOUNT])
            self.non_billable_accounts = self.generate_expenses(split_accounts[settings.TEMPO_NON_BILLABLE_ACCOUNT])
            self.non_billable_responsible_accounts = self.generate_expenses(
                split_accounts[settings.TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT])

    def generate_expenses(self, accounts: List[Account]) -> List[SustainabilityAccount]:
        """Generates aggregated worklogs for each account with `SustainabilityAccount`."""
        start_date = end_date = ''
        if self.generate_budgets:
            with connect_to_jira() as conn:
                sprints = get_all_sprints(conn)['future']
                future_sprint = sprints[0]
                start_date = get_sprint_start_date(future_sprint)
                end_date = get_sprint_end_date(future_sprint, sprints)

        args = [
            (
                {'id': account.id, 'key': account.key, 'name': account.name},
                self.cell_names, self.from_, self.to, self.generate_budgets, start_date, end_date
            ) for account in accounts if account.status == 'OPEN'
        ]

        # Use multiprocessing for parallel API requests for accounts
        with Pool(processes=settings.MULTIPROCESSING_POOL_SIZE) as pool:
            results = [pool.apply_async(SustainabilityAccount, args=arg) for arg in args]
            output = [p.get() for p in results]

        return output


class Budget(models.Model):
    """
    Stores monthly budgets for accounts.
    If the budget for the specific month is not present, the last existing one is used.
    """
    name = models.CharField(max_length=255, help_text="Account's key.")
    date = models.DateField(
        help_text="Year and month of the budget. If not specified, the last month's budget is applied."
    )
    hours = models.IntegerField(help_text="Number of available hours for this month.")

    def __str__(self):
        return f"{self.name}: {self.date.strftime('%Y-%m')}"
