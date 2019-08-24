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
    Union,
)

from django.conf import settings
# noinspection PyProtectedMember
from jira.resources import (
    Board,
    Issue,
    Project,
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

    def __init__(self, board: Board, projects: Dict[str, Project]) -> None:
        super().__init__()
        name_search = re.search(self.pattern, board.name)
        if name_search:
            self.name = name_search.group(1)
        else:
            raise AttributeError("Invalid cell name.")
        self.board_id = board.id
        self.key = projects[self.name].key


def get_cells(conn: CustomJira) -> List[Cell]:
    """Get all existing cells. Uses regexp to distinguish them from projects."""
    projects = get_projects_dict(conn)
    return [Cell(board, projects) for board in conn.boards(name=settings.JIRA_SPRINT_BOARD_PREFIX)]


def get_projects_dict(conn: CustomJira) -> Dict[str, Project]:
    """Get `Dict` of projects with their names as keys."""
    projects = conn.projects()
    return {p.name: p for p in projects}


def get_cell_members(quickfilters: List[QuickFilter]) -> List[str]:
    """Extracts the cell members' usernames from quickfilters."""
    members = []
    for quickfilter in quickfilters:
        username_search = re.search(settings.JIRA_BOARD_QUICKFILTER_PATTERN, quickfilter.query)
        if username_search:
            members.append(username_search.group(1))

    return members


def get_all_sprints(conn: CustomJira) -> Dict[str, List[Sprint]]:
    """We need to retrieve all sprints to handle cross-cell tickets."""
    cells = get_cells(conn)
    sprints = {}
    for cell in cells:
        sprints[cell.board_id] = get_sprints(conn, cell.board_id)
    result: Dict[str, List[Sprint]] = {
        'active': [],
        'future': [],
    }

    for cell_sprints in sprints.values():
        for sprint in cell_sprints:
            if sprint.state == 'active':
                result['active'].append(sprint)

    result['future'] = get_next_sprints(sprints, result['active'][0])
    return result


def get_sprints(conn: CustomJira, board_id: int) -> List[Sprint]:
    """Return the filtered list of the active and future sprints for the chosen board."""
    return conn.sprints(board_id, state='active, future')


def get_sprint_number(previous_sprint: Sprint) -> int:
    """
    Retrieves sprint number with regex and returns it as `int`.
    :raises AttributeError if the format is invalid
    """
    previous_sprint_number_search = re.search(settings.SPRINT_NUMBER_REGEX, previous_sprint.name)
    if previous_sprint_number_search:
        return int(previous_sprint_number_search.group(1))
    else:
        raise AttributeError("Invalid `previous_sprint`.")


def get_next_sprint(sprints: List[Sprint], previous_sprint: Sprint) -> Sprint:
    """
    Find the consecutive sprint by its number.
    :param sprints: a list of sprints
    :param previous_sprint: previous `Sprint`
    :returns next `Sprint` or `None` if the sprint does not exist
    """
    previous_sprint_number = get_sprint_number(previous_sprint)
    return _get_next_sprint(sprints, previous_sprint_number)


def get_next_sprints(sprints: Dict[str, List[Sprint]], previous_sprint: Sprint) -> List[Sprint]:
    """
    Find all cells' consecutive sprints by the previous sprint's number.
    :param sprints: a `Dict` of cells as keys with lists of sprints as their values
    :param previous_sprint: previous `Sprint `
    :returns list of next sprints or empty list if no next sprint exists
    """
    previous_sprint_number = get_sprint_number(previous_sprint)
    next_sprints = []
    for cell_sprints in sprints.values():
        next_sprint = _get_next_sprint(cell_sprints, previous_sprint_number)
        if next_sprint:
            next_sprints.append(next_sprint)
    return next_sprints


def get_next_cell_sprint(conn: CustomJira, board_id: int, previous_sprint: Sprint) -> Sprint:
    """
    Find the consecutive sprint in the cell by its number. It differs from `get_next_sprint`, because it retrieves the
    sprints via the API, so the list of the sprints does not need to be cached.
    """
    previous_sprint_number = get_sprint_number(previous_sprint)
    sprints = get_sprints(conn, board_id)
    return _get_next_sprint(sprints, previous_sprint_number)


def _get_next_sprint(sprints: List[Sprint], previous_sprint_number: int) -> Sprint:
    """Find the consecutive sprint by its number."""
    for sprint in sprints:
        sprint_number_search = re.search(settings.SPRINT_NUMBER_REGEX, sprint.name)
        if sprint_number_search:
            sprint_number = int(sprint_number_search.group(1))
            if previous_sprint_number + 1 == sprint_number:
                return sprint


def prepare_jql_query(sprints: List[str], fields: List[str]) -> Dict[str, Union[str, List[str]]]:
    """Prepare JQL query for retrieving stories and epics for the selected cell for the current and upcoming sprint."""
    unfinished_status = '"' + '","'.join(settings.SPRINT_STATUS_ACTIVE) + '"'
    epic_in_progress = '"' + '","'.join(settings.SPRINT_STATUS_EPIC_IN_PROGRESS) + '"'
    sprints_str = ','.join(sprints)

    query = f'(Sprint IN ({sprints_str}) AND ' \
            f'status IN ({unfinished_status})) OR (issuetype = Epic AND Status IN ({epic_in_progress}))'

    return {
        'jql_str': query,
        'fields': fields,
    }


def prepare_jql_query_active_sprint_tickets(
    fields: List[str],
    status: Iterable[str],
    project='',
) -> Dict[str, Union[str, List[str]]]:
    """Prepare JQL query for retrieving sories that spilled over before ending the sprint."""
    required_project = f'project = {project} AND ' if project else ''
    required_status = '"' + '","'.join(status) + '"'

    query = f'{required_project}Sprint IN openSprints() AND status IN ({required_status})'

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


def extract_sprint_name_from_str(sprint_str: str) -> str:
    """We're using custom field for `Sprint`, so the `sprint` field in the result is `str`."""
    pattern = r'name=(.*?),'
    search = re.search(pattern, sprint_str)
    if search:
        return search.group(1)
    raise AttributeError(f"Invalid `sprint_str`, {pattern} not found.")


def daterange(start: str, end: str) -> Generator[str, None, None]:
    """Generates days from `start_date` to `end_date` (both inclusive)."""
    start_date = datetime.strptime(start, '%Y-%m-%d')
    end_date = datetime.strptime(end, '%Y-%m-%d')
    for n in range(int((end_date - start_date).days)):
        yield (start_date + timedelta(n)).strftime('%Y-%m-%d')


def get_issue_fields(conn: CustomJira, required_fields: Iterable[str]) -> Dict[str, str]:
    """Filter Jira issue fields by their names."""
    field_ids = {field['name']: field['id'] for field in conn.fields()}
    return {field: field_ids[field] for field in required_fields}


def get_spillover_issues(conn: CustomJira, issue_fields: Dict[str, str]) -> List[Issue]:
    """Retrieves all stories and epics for the current dashboard."""
    return conn.search_issues(
        **prepare_jql_query_active_sprint_tickets(
            list(issue_fields.values()),
            settings.SPRINT_STATUS_SPILLOVER,
        ),
        maxResults=0,
    )


def prepare_spillover_rows(issues: List[Issue], issue_fields: Dict[str, str]) -> List[List[str]]:
    """
    Prepares the Google spreadsheet row in the specified format.
    Assumptions:
        - the first column contains the ID of the issue with the hyperlink to the issue,
        - the next fields are defined in `settings.SPILLOVER_REQUIRED_FIELDS`
            (the order of these fields reflects the order of the columns in the spreadsheet),
        - fields defined in `settings.JIRA_INTEGER_FIELDS` will be casted to `int`,
        - fields defined in `settings.JIRA_TIME_FIELDS` are represented in seconds (in Jira) and their final
            representation (in the spreadsheet) will be in hours rounded to 2 decimal points (if necessary).
    """
    rows = []
    for issue in issues:
        issue_url = f'=HYPERLINK("{settings.JIRA_SERVER}/browse/{issue.key}","{issue.key}")'
        row = [issue_url]
        for field in settings.SPILLOVER_REQUIRED_FIELDS:
            cell_value = getattr(issue.fields, issue_fields[field])
            if field in settings.JIRA_INTEGER_FIELDS:
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
                cell_value = tuple(cell_value)[-1]  # We need only the last sprint (when the spillover happened).

            row.append(str(cell_value))

        rows.append(row)
    return rows
