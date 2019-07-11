import re
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Dict,
    Generator,
    Iterable,
    List,
)

from django.conf import settings
# noinspection PyProtectedMember
from jira.resources import (
    Board,
    Issue,
    Sprint,
)

from sprints.dashboard.libs.jira import (
    CustomJira,
    QuickFilter,
    connect_to_jira,
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
        self.name = re.search(self.pattern, board.name).group(1)
        self.board_id = board.id


def get_cells() -> List[Cell]:
    """Get all existing cells. Uses regexp to distinguish them from projects."""
    with connect_to_jira() as conn:
        return [Cell(board) for board in conn.boards(name=settings.JIRA_SPRINT_BOARD_PREFIX)]


def get_cell_members(quickfilters: List[QuickFilter]) -> List[str]:
    """Extracts the cell members' usernames from quickfilters."""
    members = []
    for quickfilter in quickfilters:
        try:
            username = re.search(settings.JIRA_BOARD_QUICKFILTER_PATTERN, quickfilter.query).group(1)
            members.append(username)
        except AttributeError:
            # We can safely ignore non-matching filters.
            pass

    return members


def find_next_sprint(sprints: List[Sprint], previous_sprint: Sprint) -> Sprint:
    """Find the consecutive sprint by its number."""
    previous_sprint_number = int(re.search(settings.SPRINT_NUMBER_REGEX, previous_sprint.name).group(1))

    for sprint in sprints:
        if sprint.name.startswith('Sprint') and sprint.state == 'future':
            sprint_number = int(re.search(settings.SPRINT_NUMBER_REGEX, sprint.name).group(1))
            if previous_sprint_number + 1 == sprint_number:
                return sprint


def prepare_jql_query(current_sprint: int, future_sprint: int, fields: List[str]) -> Dict[str, str]:
    """Prepare JQL query for retrieving stories and epics for the selected cell for the current and upcoming sprint."""
    unfinished_status = '"' + '","'.join(
        settings.SPRINT_STATUS_SPILLOVER | {settings.SPRINT_STATUS_EXTERNAL_REVIEW,
                                            settings.SPRINT_STATUS_RECURRING}) + '"'
    epic_in_progress = '"' + '","'.join(settings.SPRINT_STATUS_EPIC_IN_PROGRESS) + '"'

    query = f'((Sprint IN {(current_sprint, future_sprint)} AND ' \
        f'status IN ({unfinished_status})) OR (issuetype = Epic AND Status IN ({epic_in_progress})))'

    return {
        'jql_str': query,
        'fields': fields,
    }


def prepare_spillover_jql_query(fields: List[str]) -> Dict[str, str]:
    """Prepare JQL query for retrieving sories that spilled over before ending the sprint."""
    spillover_status = '"' + '","'.join(settings.SPRINT_STATUS_SPILLOVER) + '"'

    query = f'Sprint IN openSprints() AND status IN ({spillover_status})'

    return {
        'jql_str': query,
        'fields': fields,
    }


def extract_sprint_id_from_str(sprint_str: str) -> int:
    """We're using custom field for `Sprint`, so the `sprint` field in the result is `str`."""
    pattern = r'id=(\d+)'
    result = re.search(pattern, sprint_str).group(1)
    return int(result)


def extract_sprint_name_from_str(sprint_str: str) -> str:
    """We're using custom field for `Sprint`, so the `sprint` field in the result is `str`."""
    pattern = r'name=(.*?),'
    return re.search(pattern, sprint_str).group(1)


def daterange(start: str, end: str) -> Generator[str, None, None]:
    """Generates days from `start_date` to `end_date` (both inclusive)."""
    start_date = datetime.strptime(start, '%Y-%m-%d')
    end_date = datetime.strptime(end, '%Y-%m-%d')
    for n in range(int((end_date - start_date).days + 1)):
        yield (start_date + timedelta(n)).strftime('%Y-%m-%d')


def get_issue_fields(conn: CustomJira, required_fields: Iterable[str]) -> Dict[str, str]:
    """Filter Jira issue fields by their names."""
    field_ids = {field['name']: field['id'] for field in conn.fields()}
    return {field: field_ids[field] for field in required_fields}


def get_spillover_issues(conn: CustomJira, issue_fields: Dict[str, str]) -> List[Issue]:
    """Retrieves all stories and epics for the current dashboard."""
    return conn.search_issues(
        **prepare_spillover_jql_query(
            list(issue_fields.values())
        ),
        maxResults=0,
    )


def prepare_spillover_rows(issues: List[Issue], issue_fields: Dict[str, str]) -> List[List[str]]:
    """Prepares the Google spreadsheet row in the specified format."""
    rows = []
    for issue in issues:
        issue_url = f'=HYPERLINK("{settings.JIRA_SERVER}/browse/{issue.key}","{issue.key}")'
        row = [issue_url]
        for field in settings.SPILLOVER_REQUIRED_FIELDS:
            cell_value = getattr(issue.fields, issue_fields[field])
            if field in settings.JIRA_NUMERIC_FIELDS:
                try:
                    cell_value = int(cell_value)
                except TypeError:
                    # Ignore `None` values.
                    pass
            if field in settings.JIRA_TIME_FIELDS:
                try:
                    cell_value = round(cell_value / 3600, 2)
                except TypeError:
                    # Ignore `None` values.
                    pass
            if field == 'Sprint':
                cell_value = map(extract_sprint_name_from_str, cell_value)
                cell_value = '\n'.join(cell_value)

            row.append(str(cell_value))

        rows.append(row)
    return rows
