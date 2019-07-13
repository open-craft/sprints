import re
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Dict,
    Generator,
    List,
    Union,
)

from django.conf import settings
# noinspection PyProtectedMember
from jira.resources import (
    Board,
    Sprint,
)

from sprints.dashboard.libs.jira import (
    CustomJira,
    QuickFilter,
)

SECONDS_IN_HOUR = 3600


class Cell:
    """
    Model representing cell - its name and sprint board ID.
    It is placed in `utils` to avoid circular imports for type checks.
    """
    pattern = fr'{settings.JIRA_SPRINT_BOARD_PREFIX}(.*)'

    def __init__(self, board: Board) -> None:
        super().__init__()
        name_search = re.search(self.pattern, board.name)
        if name_search:
            self.name = name_search.group(1)
        else:
            raise AttributeError("Invalid cell name.")
        self.board_id = board.id


def get_cells(conn: CustomJira) -> List[Cell]:
    """Get all existing cells. Uses regexp to distinguish them from projects."""
    return [Cell(board) for board in conn.boards(name=settings.JIRA_SPRINT_BOARD_PREFIX)]


def get_cell_members(quickfilters: List[QuickFilter]) -> List[str]:
    """Extracts the cell members' usernames from quickfilters."""
    members = []
    for quickfilter in quickfilters:
        username_search = re.search(settings.JIRA_BOARD_QUICKFILTER_PATTERN, quickfilter.query)
        if username_search:
            members.append(username_search.group(1))

    return members


def find_next_sprint(sprints: List[Sprint], previous_sprint: Sprint) -> Sprint:
    """Find the consecutive sprint by its number."""
    previous_sprint_number_search = re.search(settings.SPRINT_NUMBER_REGEX, previous_sprint.name)
    if previous_sprint_number_search:
        previous_sprint_number = int(previous_sprint_number_search.group(1))
    else:
        raise AttributeError("Invalid `previous_sprint`.")

    for sprint in sprints:
        if sprint.name.startswith('Sprint') and sprint.state == 'future':
            sprint_number_search = re.search(settings.SPRINT_NUMBER_REGEX, sprint.name)
            if sprint_number_search:
                sprint_number = int(sprint_number_search.group(1))
                if previous_sprint_number + 1 == sprint_number:
                    return sprint


def prepare_jql_query(current_sprint: int, future_sprint: int, fields: List[str]) -> Dict[str, Union[str, List[str]]]:
    """Prepare JQL query for retrieving stories and epics for the selected cell for the current and upcoming sprint."""
    unfinished_status = '"' + '","'.join(settings.SPRINT_STATUS_UNFINISHED | {settings.SPRINT_STATUS_RECURRING}) + '"'
    epic_in_progress = '"' + '","'.join(settings.SPRINT_STATUS_EPIC_IN_PROGRESS) + '"'

    query = f'(Sprint IN {(current_sprint, future_sprint)} AND ' \
        f'status IN ({unfinished_status})) OR (issuetype = Epic AND Status IN ({epic_in_progress}))'

    return {
        'jql_str': query,
        'fields': fields,
    }


def extract_sprint_id_from_str(sprint_str: str) -> int:
    """We're using custom field for `Sprint`, so the `sprint` field in the result is `str`."""
    pattern = r'id=(\d+)'
    search = re.search(pattern, sprint_str)
    if search:
        return int(search.group(1))
    raise AttributeError(f"Invalid `sprint_str`, {pattern} not found.")


def daterange(start: str, end: str) -> Generator[str, None, None]:
    """Generates days from `start_date` to `end_date` (both inclusive)."""
    start_date = datetime.strptime(start, '%Y-%m-%d')
    end_date = datetime.strptime(end, '%Y-%m-%d')
    for n in range(int((end_date - start_date).days + 1)):
        yield (start_date + timedelta(n)).strftime('%Y-%m-%d')
