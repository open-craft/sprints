import calendar
from datetime import datetime
from typing import (
    Dict,
    Generator,
    List,
    Tuple,
)

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from sprints.dashboard.libs.jira import (
    Account,
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


def on_error(e: BaseException):
    """Callback method for retrieving exceptions from async processes."""
    raise e
