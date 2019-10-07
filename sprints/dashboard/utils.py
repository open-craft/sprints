import re
import string
import time
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
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

from sprints.dashboard.libs.google import get_availability_spreadsheet
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


def get_cell_member_names(conn: CustomJira, members: Iterable[str]) -> Dict[str, str]:
    """Returns cell members with their names."""
    return {conn.user(member).displayName: member for member in members}


def get_all_sprints(conn: CustomJira, board_id: Optional[int] = None) -> Dict[str, List[Sprint]]:
    """We need to retrieve all sprints to handle cross-cell tickets."""
    cells = get_cells(conn)
    sprints = {}
    cell_key: Optional[str] = None
    for cell in cells:
        sprints[cell.board_id] = get_sprints(conn, cell.board_id)
        if cell.board_id == board_id:
            cell_key = cell.key

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
            if cell_key and sprint.name.startswith(cell_key):
                result.setdefault('cell', []).append(sprint)

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
    previous_sprint_number_search = re.search(settings.SPRINT_REGEX, previous_sprint.name)
    if previous_sprint_number_search:
        return int(previous_sprint_number_search.group(2))
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
        sprint_number_search = re.search(settings.SPRINT_REGEX, sprint.name)
        if sprint_number_search:
            sprint_number = int(sprint_number_search.group(2))
            if previous_sprint_number + 1 == sprint_number:
                if not many:
                    return sprint
                result.append(sprint)

    return result if many else None


def get_sprint_start_date(sprint: Sprint) -> str:
    """Returns start date of the sprint."""
    if getattr(sprint, 'startDate', None):
        return sprint.startDate.split('T')[0]

    return extract_sprint_start_date_from_sprint_name(sprint.name)


def get_sprint_end_date(sprint: Sprint, sprints: List[Sprint]) -> str:
    """Returns end date of the sprint -1 day, because that's when the new sprint starts."""
    if getattr(sprint, 'endDate', None):
        date = sprint.endDate.split('T')[0]
    else:
        future_sprint = get_next_sprint(sprints, sprint)
        date = get_sprint_start_date(future_sprint)

    return (parse(date) - timedelta(days=1)).strftime("%Y-%m-%d")


def filter_sprints_by_cell(sprints: List[Sprint], key: str) -> List[Sprint]:
    """Filters sprints created for the specific cell. We're using cell's key for finding the suitable sprints."""
    return [sprint for sprint in sprints if sprint.name.startswith(key)]


def prepare_jql_query(
    sprints: List[str],
    fields: List[str],
    user: Optional[str] = None
) -> Dict[str, Union[str, List[str]]]:
    """Prepare JQL query for retrieving stories and epics for the selected cell for the current and upcoming sprint."""
    unfinished_status = '"' + '","'.join(settings.SPRINT_STATUS_ACTIVE) + '"'
    epic_in_progress = '"' + '","'.join(settings.SPRINT_STATUS_EPIC_IN_PROGRESS) + '"'
    sprints_str = ','.join(sprints)
    user_str = f'(assignee = "{user}" OR "Reviewer 1" = "{user}") AND ' if user else ''

    query = f'({user_str}Sprint IN ({sprints_str}) AND ' \
            f'status IN ({unfinished_status})) OR ({user_str}issuetype = Epic AND Status IN ({epic_in_progress}))'

    return {
        'jql_str': query,
        'fields': fields,
    }


def prepare_jql_query_active_sprint_tickets(
    fields: List[str],
    status: Iterable[str],
    project='',
    summary='',
) -> Dict[str, Union[str, List[str]]]:
    """Prepare JQL query for retrieving stories that spilled over before ending the sprint."""
    required_project = f'project = {project} AND ' if project else ''
    required_status = '"' + '","'.join(status) + '"'
    required_summary = f" AND summary ~ {summary}" if summary else ''

    query = f'{required_project}Sprint IN openSprints() AND status IN ({required_status}){required_summary}'

    return {
        'jql_str': query,
        'fields': fields,
    }


def prepare_jql_query_cell_role_epic(fields: List[str], project: str) -> Dict[str, Union[str, List[str]]]:
    """Prepare JQL query for retrieving epic for the cell role tickets."""
    query = f'summary ~ {settings.JIRA_CELL_ROLE_EPIC_NAME} AND project = {project} AND ' \
            f'status = {settings.SPRINT_STATUS_RECURRING} AND issuetype = Epic'

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
    search = re.search(settings.SPRINT_REGEX, sprint_name)
    if search:
        return search.group(3)
    raise AttributeError(f"Invalid sprint name, {settings.SPRINT_REGEX} not found.")


def daterange(start: str, end: str) -> Generator[str, None, None]:
    """Generates days from `start_date` to `end_date` (both inclusive)."""
    start_date = datetime.strptime(start, settings.JIRA_API_DATE_FORMAT)
    end_date = datetime.strptime(end, settings.JIRA_API_DATE_FORMAT)
    for n in range(int((end_date - start_date).days)):
        yield (start_date + timedelta(n)).strftime(settings.JIRA_API_DATE_FORMAT)


def get_issue_fields(conn: CustomJira, required_fields: Iterable[str]) -> Dict[str, str]:
    """Filter Jira issue fields by their names."""
    field_ids = {field['name']: field['id'] for field in conn.fields()}
    return {field: field_ids[field] for field in required_fields}


def get_spillover_issues(conn: CustomJira, issue_fields: Dict[str, str], project: str = '') -> List[Issue]:
    """Retrieves all stories and epics for the current dashboard."""
    return conn.search_issues(
        **prepare_jql_query_active_sprint_tickets(
            list(issue_fields.values()),
            settings.SPRINT_STATUS_SPILLOVER,
            project=project,
        ),
        maxResults=0,
    )


def get_meetings_issue(conn: CustomJira, project: str, issue_fields: Dict[str, str]) -> Issue:
    """
    Retrieves the Jira issue used for logging the meetings. We're using this for collecting hints for achieving
    clean sprints. It is a workaround for JQL inability to do exact match.
    https://community.atlassian.com/t5/Jira-Core-questions/How-to-query-Summary-for-EXACT-match/qaq-p/588482
    """
    issues = conn.search_issues(
        **prepare_jql_query_active_sprint_tickets(
            list(issue_fields.values()) + ['summary'],
            (settings.SPRINT_STATUS_RECURRING,),
            project=project,
            summary=settings.SPRINT_MEETINGS_TICKET,
        ),
        maxResults=0,
    )

    for issue in issues:
        if issue.fields.summary == settings.SPRINT_MEETINGS_TICKET:
            return issue


def create_next_sprint(conn: CustomJira, sprints: List[Sprint], cell_key: str, board_id: int) -> None:
    """Creates next sprint for the desired cell."""
    sprints = filter_sprints_by_cell(sprints, cell_key)
    last_sprint = sprints[-1]
    end_date = parse(last_sprint.endDate)

    future_next_sprint_number = get_sprint_number(last_sprint) + 1
    future_name_date = (end_date + timedelta(days=1)).strftime(settings.JIRA_API_DATE_FORMAT)
    future_end_date = end_date + timedelta(days=settings.SPRINT_DURATION_DAYS)
    conn.create_sprint(
        name=f'{cell_key}.{future_next_sprint_number} ({future_name_date})',
        board_id=board_id,
        startDate=end_date.isoformat(),
        endDate=future_end_date.isoformat(),
    )


def get_spillover_reason(issue: Issue, issue_fields: Dict[str, str], sprint: Sprint, assignee: str) -> str:
    """Retrieve the spillover reason from the comment matching the `settings.SPILLOVER_REASON_DIRECTIVE` regexp."""
    # For issues spilling over more than once we need to ensure that the comment has been added in the current sprint.
    sprint_start_date = parse(sprint.startDate)

    # Check each comment created after starting the current sprint.
    comments = getattr(issue.fields, issue_fields['Comment']).comments
    for comment in reversed(comments):  # type: Comment
        if assignee != comment.author.displayName:
            continue

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
                cell_value = get_spillover_reason(
                    issue,
                    issue_fields,
                    current_sprint,
                    getattr(issue.fields, issue_fields['Assignee']).displayName
                )

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


def prepare_clean_sprint_rows(
    rows: List[List[str]],
    members: Dict[str, str],
    meetings: Issue,
    issue_fields: Dict[str, str],
    sprints: Dict[int, Sprint],
) -> None:
    """Adds the Google spreadsheet row in the specified format for users who achieved clean sprint."""
    # +1 for the issue's key
    status_index = settings.SPILLOVER_REQUIRED_FIELDS.index("Status") + 1
    sprint_index = settings.SPILLOVER_REQUIRED_FIELDS.index("Sprint") + 1
    assignee_index = settings.SPILLOVER_REQUIRED_FIELDS.index("Assignee") + 1

    members_with_spillovers = {row[assignee_index] for row in rows}
    members_with_clean_sprint = members.keys() - members_with_spillovers - settings.SPILLOVER_CLEAN_SPRINT_IGNORED_USERS

    sprint = getattr(meetings.fields, issue_fields['Sprint'])[-1]
    current_sprint = sprints[extract_sprint_id_from_str(sprint)]

    for member in members_with_clean_sprint:
        row = [''] * (len(settings.SPILLOVER_REQUIRED_FIELDS) + 1)
        row[0] = "Clean sprint"
        row[status_index] = "Done"
        row[sprint_index] = extract_sprint_name_from_str(sprint)
        row[assignee_index] = member
        row[-1] = get_spillover_reason(meetings, issue_fields, current_sprint, member)

        # If the reason hasn't been posted, add comment with the reminder to the issue.
        if not row[-1] and not settings.DEBUG:  # We don't want to ping people via the dev environment.
            from sprints.dashboard.tasks import add_spillover_reminder_comment_task  # Avoid circular import.
            add_spillover_reminder_comment_task.delay(meetings.key, members[member], clean_sprint=True)

        rows.append(row)


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


def _get_sprint_meeting_day_division_for_member(hours: str) -> float:
    """
    Helper method for determining at which point of the member's working day is the sprint meeting.
    It handles the "minus" and "plus" timezones by adding the `-` at the end of the availability string.

    For invalid time format, 0 (before the working day) is assumed, but the error is logged to Sentry.
    """
    hours = hours.replace('*', '').replace(' ', '')  # Strip unnecessary characters
    minus_timezone = hours.endswith('-')
    search = re.search(settings.GOOGLE_AVAILABILITY_REGEX, hours)
    try:
        start_str = f"{search.group(1)}{search.group(2)}"  # type: ignore
        end_str = f"{search.group(3)}{search.group(4)}"  # type: ignore
        start_hour = time.strptime(start_str, settings.GOOGLE_AVAILABILITY_TIME_FORMAT).tm_hour
        end_hour = time.strptime(end_str, settings.GOOGLE_AVAILABILITY_TIME_FORMAT).tm_hour
        if end_hour == 0:
            end_hour = 24
    except (AttributeError, TypeError, ValueError) as e:
        # Log exception to Sentry if the format is invalid, but do not break the server.
        from sentry_sdk import capture_exception
        capture_exception(e)
        return 0

    if end_hour < start_hour:  # Special case
        if minus_timezone:
            end_hour = 24
        else:
            start_hour = 0

    available_hours = end_hour - start_hour
    meeting_relative = settings.SPRINT_MEETING_HOUR_UTC - start_hour
    meeting_division = max(min(meeting_relative / available_hours, 1), 0)
    return meeting_division


def get_sprint_meeting_day_division() -> Dict[str, float]:
    """
    Returns how much of the members' days is before the sprint meeting.
    Example:
        - 1. means that the meeting is after the set working day,
        - 0. means that the meeting is before the set working day,
        - .75 means that the meeting is in the third quarter of the set working day
          (e.g. the member is working from 12 to 20 and the meeting is at 18).
    """
    spreadsheet = get_availability_spreadsheet()
    result = {}

    for row in spreadsheet[2:]:
        if row[0] and row[1]:
            result[row[0]] = _get_sprint_meeting_day_division_for_member(row[1])
        else:
            # Ignore instructions and explanations added below the availability list.
            break

    return result
