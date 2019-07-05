import re
from typing import (
    Dict,
    List,
)

# noinspection PyProtectedMember
from jira.resources import (
    Sprint,
)

from config.settings.base import (
    JIRA_BOARD_QUICKFILTER_PATTERN,
    JIRA_SPRINT_BOARD_PREFIX,
    SPRINT_NUMBER_REGEX,
    SPRINT_STATUS_EPIC_IN_PROGRESS,
    SPRINT_STATUS_RECURRING,
    SPRINT_STATUS_UNFINISHED,
)
from sprints.dashboard.libs.jira import (
    QuickFilter,
    connect_to_jira,
)
from sprints.dashboard.models import Cell

SECONDS_IN_HOUR = 3600


def get_cells() -> List[Cell]:
    """Get all existing cells. Uses regexp to distinguish them from projects."""
    with connect_to_jira() as conn:
        return [Cell(board) for board in conn.boards(name=JIRA_SPRINT_BOARD_PREFIX)]


def get_cell_members(quickfilters: List[QuickFilter]) -> List[str]:
    """Extracts the cell members' usernames from quickfilters."""
    members = []
    for quickfilter in quickfilters:
        try:
            username = re.search(JIRA_BOARD_QUICKFILTER_PATTERN, quickfilter.query).group(1)
            members.append(username)
        except AttributeError:
            # We can safely ignore non-matching filters.
            pass

    return members


def find_next_sprint(sprints: List[Sprint], previous_sprint: Sprint) -> Sprint:
    """Find the consecutive sprint by its number."""
    previous_sprint_number = int(re.search(SPRINT_NUMBER_REGEX, previous_sprint.name).group(1))

    for sprint in sprints:
        if sprint.name.startswith('Sprint') and sprint.state == 'future':
            sprint_number = int(re.search(SPRINT_NUMBER_REGEX, sprint.name).group(1))
            if previous_sprint_number + 1 == sprint_number:
                return sprint


def prepare_jql_query(current_sprint: int, future_sprint: int, fields: List[str]) -> Dict[str, str]:
    """Prepare JQL query for retrieving stories and epics for the selected cell for the current and upcoming sprint."""
    unfinished_status = '"' + '","'.join(SPRINT_STATUS_UNFINISHED | {SPRINT_STATUS_RECURRING}) + '"'
    epic_in_progress = '"' + '","'.join(SPRINT_STATUS_EPIC_IN_PROGRESS) + '"'

    query = f'((Sprint IN {(current_sprint, future_sprint)} and ' \
        f'status IN ({unfinished_status})) OR (issuetype = Epic AND Status IN ({epic_in_progress})))'

    return {
        'jql_str': query,
        'fields': fields,
    }


def extract_sprint_id_from_str(sprint_str: str) -> int:
    """We're using custom field for `Sprint`, so the `sprint` field in the result is `str`."""
    pattern = r'id=(\d+)'
    result = re.search(pattern, sprint_str).group(1)
    return int(result)
