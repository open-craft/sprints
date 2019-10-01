import re
from multiprocessing.pool import Pool
from typing import (
    Dict,
    List,
    Union,
)

from django.conf import settings

from sprints.dashboard.libs.jira import (
    Account,
    CustomJira,
    connect_to_jira,
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

    def __init__(self, account: Dict[str, Union[str, int]], cell_names: Dict[str, str], from_: str, to: str) -> None:
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
        args = [
            ({'id': account.id, 'key': account.key, 'name': account.name}, self.cell_names, self.from_, self.to)
            for account in accounts if account.status == 'OPEN'
        ]

        # Use multiprocessing for parallel API requests for accounts
        with Pool(processes=settings.MULTIPROCESSING_POOL_SIZE) as pool:
            results = [pool.apply_async(SustainabilityAccount, args=arg) for arg in args]
            output = [p.get() for p in results]

        return output
