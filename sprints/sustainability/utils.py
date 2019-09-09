from typing import (
    Dict,
    List,
)

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
