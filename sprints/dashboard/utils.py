import re
import string
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
    Tuple,
)

from dateutil.parser import parse
from django.conf import settings
# noinspection PyProtectedMember
from jira.resources import (
    Board,
    Comment,
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
        'all': [],
    }

    for cell_sprints in sprints.values():
        for sprint in cell_sprints:
            result['all'].append(sprint)
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
    result: List[Sprint] = []
    for cell_sprints in sprints.values():
        next_sprints = _get_next_sprint(cell_sprints, previous_sprint_number, many=True)
        result.extend(next_sprints)
    return result


def get_next_cell_sprint(conn: CustomJira, board_id: int, previous_sprint: Sprint) -> Sprint:
    """
    Find the consecutive sprint in the cell by its number. It differs from `get_next_sprint`, because it retrieves the
    sprints via the API, so the list of the sprints does not need to be cached.
    """
    previous_sprint_number = get_sprint_number(previous_sprint)
    sprints = get_sprints(conn, board_id)
    return _get_next_sprint(sprints, previous_sprint_number)


def _get_next_sprint(sprints: List[Sprint], previous_sprint_number: int, many=False) -> Union[Sprint, List[Sprint]]:
    """
    Find the consecutive sprint by its number.
    :param many: if `True`, return `list` of next sprints (with the same number)
    """
    result: List[Sprint] = []

    for sprint in sprints:
        sprint_number_search = re.search(settings.SPRINT_NUMBER_REGEX, sprint.name)
        if sprint_number_search:
            sprint_number = int(sprint_number_search.group(1))
            if previous_sprint_number + 1 == sprint_number:
                if not many:
                    return sprint
                result.append(sprint)

    return result if many else None


def get_sprint_start_date(sprint: Sprint) -> str:
    if getattr(sprint, 'startDate', None):
        return sprint.startDate.split('T')[0]

    return extract_sprint_start_date_from_sprint_name(sprint.name)


def get_sprint_end_date(sprint: Sprint, sprints: List[Sprint]) -> str:
    if getattr(sprint, 'endDate', None):
        return sprint.endDate.split('T')[0]

    future_sprint = get_next_sprint(sprints, sprint)
    return get_sprint_start_date(future_sprint)


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
    pattern = r'name=(.*?\))'
    search = re.search(pattern, sprint_str)
    if search:
        return search.group(1)
    raise AttributeError(f"Invalid `sprint_str`, {pattern} not found.")


def extract_sprint_start_date_from_sprint_name(sprint_name: str) -> str:
    """Extract sprint start date from sprint's name."""
    search = re.search(settings.SPRINT_DATE_REGEX, sprint_name)
    if search:
        return search.group(1)
    raise AttributeError(f"Invalid sprint name, {settings.SPRINT_DATE_REGEX} not found.")


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


def get_spillover_reason(issue: Issue, issue_fields: Dict[str, str], sprint: Sprint) -> str:
    """Retrieve the spillover reason from the comment matching the `settings.SPILLOVER_REASON_DIRECTIVE` regexp."""
    # For issues spilling over more than once we need to ensure that the comment has been added in the current sprint.
    sprint_start_date = parse(sprint.startDate)

    # Check each comment created after starting the current sprint.
    for comment in reversed(getattr(issue.fields, issue_fields['Comment']).comments):  # type: Comment
        created_date = parse(comment.created)
        if created_date < sprint_start_date:
            break

        search = re.search(settings.SPILLOVER_REASON_DIRECTIVE, comment.body)
        if search:
            return search.group(1)

    return ''


def prepare_spillover_rows(
    issues: List[Issue],
    issue_fields: Dict[str, str],
    sprints: Dict[int, Sprint]
) -> List[List[str]]:
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
        current_sprint = None

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
                original_value = cell_value
                cell_value = extract_sprint_name_from_str(original_value[-1])
                current_sprint = sprints[extract_sprint_id_from_str(original_value[-1])]

            if field == 'Comment':
                # Retrieve the spillover reason.
                cell_value = get_spillover_reason(issue, issue_fields, current_sprint)

                # If the reason hasn't been posted, add comment with the reminder to the issue.
                if not cell_value and not settings.DEBUG:  # We don't want to ping people via the dev environment.
                    from sprints.dashboard.tasks import add_spillover_reminder_comment_task  # Avoid circular import.
                    add_spillover_reminder_comment_task.delay(
                        issue.key,
                        getattr(issue.fields, issue_fields['Assignee']).key,
                    )

            row.append(str(cell_value))

        rows.append(row)
    return rows


def prepare_commitment_spreadsheet(dashboard, spreadsheet: List[List[str]]) -> Tuple[List[str], List[str]]:
    """Prepare list of new members (ones that are not present in the spreadsheet) and commitments for all members."""
    sprint_number = int(spreadsheet[-1][0]) + 1
    users: List[str] = []
    column: List[str] = [str(sprint_number)]
    commitments: Dict[str, int] = {
        row.user.displayName: row.remaining_time
        for row in dashboard.rows
        if hasattr(row.user, 'displayName')
    }

    # Process existing users.
    for user in spreadsheet[0][1:]:
        try:
            column.append(str(round(int(commitments.pop(user, '-')) / SECONDS_IN_HOUR)))
        except (TypeError, ValueError):
            column.append('-')

    # Process the users that don't exist in the spreadsheet yet.
    for user, commitment in commitments.items():
        users.append(user)
        column.append(str(round(commitment / SECONDS_IN_HOUR)))

    return users, column


def get_commitment_range(spreadsheet: List[List[str]], cell_name: str) -> str:
    """Retrieve the proper range for the spreadsheet, depending on the cell and number of currently stored sprints."""
    column_number = base_10_to_n(len(spreadsheet), len(string.ascii_uppercase))
    return f"'{cell_name} Commitments'!{column_number}3"


def base_10_to_n(num: int, b: int, numerals: str = string.ascii_uppercase) -> str:
    """Convert `num` to the desired base `b` with selected `numerals`"""
    return ((num == 0) and numerals[0]) or (base_10_to_n(num // b, b, numerals).lstrip(numerals[0]) + numerals[num % b])
