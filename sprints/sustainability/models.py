import re
from typing import (
    Dict,
    List,
)

from django.conf import settings

from sprints.dashboard.libs.jira import (
    Account,
    CustomJira,
    Expense,
)
from sprints.dashboard.utils import (
    get_cells,
)
from sprints.sustainability.utils import split_accounts_into_categories


class SustainabilityAccount:
    """
    Aggregates account name and key along with:
        - overall time spent on the account,
        - cell-specific time spent on the account,
        - person-specific time spent on the account.
    """

    def __init__(self, account: Account, expenses: Expense, cell_names: Dict[str, str]) -> None:
        self.key = account.key
        self.name = account.name
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


class SustainabilityDashboard:
    """
    Aggregates accounts into a single dashboard.
    """

    def __init__(self, conn: CustomJira, from_: str, to: str) -> None:
        self.jira_connection = conn
        self.from_ = from_
        self.to = to

        accounts: List[Account] = self.jira_connection.accounts()
        split_accounts = split_accounts_into_categories(accounts)
        cells = get_cells(self.jira_connection)
        self.cell_names = {cell.key: cell.name for cell in cells}

        self.billable_accounts = self.generate_expenses(split_accounts[settings.TEMPO_BILLABLE_ACCOUNT])
        self.non_billable_accounts = self.generate_expenses(split_accounts[settings.TEMPO_NON_BILLABLE_ACCOUNT])
        self.non_billable_responsible_accounts = self.generate_expenses(
            split_accounts[settings.TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT])

    def generate_expenses(self, accounts: List[Account]) -> List[SustainabilityAccount]:
        """Generates aggregated worklogs for each account with `SustainabilityAccount`."""
        result = []
        for account in accounts:
            # We don't want to calculate closed accounts here.
            if account.status != 'OPEN':
                continue

            expenses = self.jira_connection.expenses(account.id, self.from_, self.to)
            result.append(SustainabilityAccount(account, expenses, self.cell_names))
        return result
