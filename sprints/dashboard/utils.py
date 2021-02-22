import re
import string
import requests
from collections import defaultdict
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    DefaultDict,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

# noinspection PyUnresolvedReferences,PyPackageRequirements
from dateutil.parser import (
    ParserError,
    parse,
)
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import (
    ImproperlyConfigured,
    ValidationError,
)
from django.core.validators import URLValidator
# noinspection PyProtectedMember
from jira.resources import (
    Board,
    Comment,
    Issue,
    Project,
    Sprint,
    User,
)

from config.settings.base import SECONDS_IN_HOUR
from sprints.dashboard.libs.google import get_availability_spreadsheet
from sprints.dashboard.libs.jira import (
    CustomJira,
    QuickFilter,
    connect_to_jira,
)


class NoRolesFoundException(Exception):
    pass


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


def get_cell(conn: CustomJira, board_id: int) -> Cell:
    """
    Retrieves the cell owning the sprint board.

    :raises ValueError if the cell was not found (this can happen when the board is not a sprint board)
    """
    for cell in get_cells(conn):
        if cell.board_id == board_id:
            return cell
    raise ValueError("Cell not found.")


def get_cell_members(quickfilters: List[QuickFilter]) -> List[str]:
    """Extracts the cell members' usernames from quickfilters."""
    members = []
    for quickfilter in quickfilters:
        username_search = re.search(settings.JIRA_BOARD_QUICKFILTER_PATTERN, quickfilter.query)
        if username_search:
            members.append(username_search.group(1))

    return members


def get_cell_membership(conn: CustomJira) -> dict[str, str]:
    """
    Get a dict with users and their cell membership for querying it by user.

    :param conn: Jira connection.
    :return: Dict with `user: cell_name` entries.
    """
    cells = get_cells(conn)
    cell_membership = {}

    for cell in cells:
        quickfilters = conn.quickfilters(cell.board_id)
        members = get_cell_members(quickfilters)
        for member in members:
            cell_membership[member] = cell.name

    return cell_membership


def get_cell_member_names(conn: CustomJira, members: Iterable[str]) -> Dict[str, str]:
    """Returns cell members with their names."""
    return {conn.user(member).displayName: member for member in members}


def get_cell_member_roles() -> DefaultDict[str, List[str]]:
    """
    Return a dictionary of cell members and their associated roles.

    Example return: `{'John Doe': ['Recruitment Manager', 'Sprint Planning Manager',...],...}`

    Note: we are using the following sources of data for this function:
        1. Handbook (cell roles, e.g. "Sprint Planning Manager").
        2. Rotations spreadsheet (sprint roles - e.g. "Firefighter", "Discovery Duty")
        3. Jira (matching users with their email addresses).
    Therefore we should ensure that users' names don't contain any typos, as this will provide inaccurate results.
    """

    if settings.FEATURE_CELL_ROLES:
        try:
            URLValidator(settings.HANDBOOK_ROLES_PAGE)
        except ValidationError:
            raise ImproperlyConfigured(
                f"Handbook roles page ({settings.HANDBOOK_ROLES_PAGE}) specified is not a valid url"
            )

    r = requests.get(settings.HANDBOOK_ROLES_PAGE)

    # roles = [('Recruitment manager', 'John Doe'),('Sprint Planning Manager', 'John Doe'),...]
    roles = re.findall(settings.ROLES_REGEX, r.text)

    # roles_dict = {'John Doe': ['Recruitment Manager', 'Sprint Planning Manager',...],...}
    roles_dict = defaultdict(list)
    for role, member in roles:
        roles_dict[member].append(role)

    # If we haven't read any roles, then something must have went wrong.
    if len(roles_dict) == 0:
        raise NoRolesFoundException(f"No roles were found at the handbook page: {settings.HANDBOOK_ROLES_PAGE}")

    return roles_dict


def compile_participants_roles(
    members: List[User],
    rotations: Dict[str, List[str]],
    cell_member_roles: DefaultDict[str, List[str]]
) -> DefaultDict[str, List[str]]:
    """Compile the final roles Dictionary from `cell_member_roles` and `rotations` data"""

    roles: DefaultDict[str, List[str]] = defaultdict(list)
    for member in members:
        roles[member.emailAddress].extend(cell_member_roles[member.displayName])
        roles[member.emailAddress].extend(get_rotations_roles_for_member(member.displayName, rotations))

    return roles


def get_rotations_roles_for_member(member_name: str, rotations: Dict[str, List[str]]) -> List[str]:
    """
    Retrieve rotation roles for a member.
    :param member_name: a string representing the member's name
    :param rotations: a dictionary containing `get_rotations_users()` output
    :returns a list of all roles for that user.
    """
    roles = []

    for duty, assignees in rotations.items():
        # Enumeration is used for determining the order of roles in a sprint - e.g. `FF-1`, `DD-2`, etc.
        for idx, assignee in enumerate(assignees):
            if member_name.startswith(assignee):
                roles.append(f"{duty}-{idx + 1}")
    return roles


def get_all_sprints(conn: CustomJira, board_id: Optional[int] = None) -> Dict[str, List[Sprint]]:
    """Retrieves all sprints (used for handling cross-cell tickets)."""
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

    if board_id:
        result['future'] = get_next_sprints(sprints, result['cell'][0])
    else:
        result['future'] = get_next_sprints(sprints, result['active'][0])

    # Each sprint can appear once for every cell if there are any cross-cell tickets in it. We should remove duplicates.
    for sprint_type, sprints_of_type in result.items():
        result[sprint_type] = remove_duplicates_by_attribute(sprints_of_type, 'id')

    return result


def get_sprints(conn: CustomJira, board_id: int) -> List[Sprint]:
    """Return the filtered list of the active and future sprints for the chosen board."""
    return conn.sprints(board_id, state='active, future')


def get_sprint_number(sprint: Sprint) -> int:
    """
    Retrieves sprint number with regex and returns it as `int`.
    :raises AttributeError if the format is invalid
    """
    sprint_number_search = re.search(settings.SPRINT_REGEX, sprint.name)
    if sprint_number_search:
        return int(sprint_number_search.group(2))
    else:
        raise AttributeError(f'The sprint name ("{sprint.name}") does not match the "{settings.SPRINT_REGEX}" regex.')


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
    return extract_sprint_start_date_from_sprint_name(sprint.name)


def get_sprint_end_date(sprint: Sprint) -> str:
    """Get the last day of the sprint."""
    date = get_sprint_start_date(sprint)
    return _get_sprint_end_date(date)


def _get_sprint_end_date(date_str: str) -> str:
    """Get the last day of the sprint, given the sprint start date."""
    end_date = (parse(date_str) + timedelta(days=settings.SPRINT_DURATION_DAYS - 1))
    return end_date.strftime(settings.JIRA_API_DATE_FORMAT)


def get_current_sprint_start_date(sprint_type='active', board_id: str = '') -> str:
    """Get the cached start of sprint date for speeding up more frequent requests."""
    if not (result := cache.get(f"{settings.CACHE_SPRINT_START_DATE_PREFIX}{sprint_type}{board_id}")):
        result = cache.get_or_set(
            f"{settings.CACHE_SPRINT_START_DATE_PREFIX}{sprint_type}{board_id}",
            get_sprint_start_date(_get_current_sprint(sprint_type, int(board_id) if board_id else None)),
            settings.CACHE_SPRINT_DATES_TIMEOUT_SECONDS
        )
    return result


def get_current_sprint_end_date(sprint_type='active', board_id: str = '') -> str:
    """Get the cached end of sprint date for speeding up more frequent requests."""
    start_str = get_current_sprint_start_date(sprint_type, board_id)
    return _get_sprint_end_date(start_str)


def _get_current_sprint(type_: str, board_id: int = None) -> Sprint:
    """Get the current sprint. `type_` can be set to `active` or `future`."""
    with connect_to_jira() as conn:
        sprints = get_all_sprints(conn, board_id)[type_]

    return sprints[0]


def filter_sprints_by_cell(sprints: List[Sprint], key: str) -> List[Sprint]:
    """Filters sprints created for the specific cell. We're using cell's key for finding the suitable sprints."""
    return [sprint for sprint in sprints if sprint.name.startswith(key)]


def get_sprint_by_name(conn: CustomJira, sprint_name: str) -> Sprint:
    """
    Get the sprint with a specified name.

    :param conn: Jira connection.
    :param sprint_name: Name of the sprint that needs to be found.
    :raise ImproperlyConfigured: Sprint with the desired name does not exist.
    :return: Sprint with the desired name.
    """
    sprints = get_all_sprints(conn)
    for sprint in sprints['all']:
        if sprint.name == sprint_name:
            return sprint

    raise ImproperlyConfigured(f'Could not find the "{settings.SPRINT_ASYNC_INJECTION_SPRINT}" sprint.')


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
    for n in range(int((end_date - start_date).days + 1)):
        yield (start_date + timedelta(n)).strftime(settings.JIRA_API_DATE_FORMAT)


def get_issue_fields(conn: CustomJira, required_fields: Iterable[str]) -> Dict[str, str]:
    """Filter Jira issue fields by their names."""
    return {field: conn.issue_fields[field] for field in required_fields}


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


def create_next_sprint(conn: CustomJira, sprints: List[Sprint], cell_key: str, board_id: int) -> Sprint:
    """Creates next sprint for the desired cell."""
    sprints = filter_sprints_by_cell(sprints, cell_key)
    last_sprint = sprints[-1]
    end_date = parse(last_sprint.endDate)

    future_next_sprint_number = get_sprint_number(last_sprint) + 1
    future_name_date = (end_date + timedelta(days=1)).strftime(settings.JIRA_API_DATE_FORMAT)
    future_end_date = end_date + timedelta(days=settings.SPRINT_DURATION_DAYS)
    return conn.create_sprint(
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
                # Jira orders sprints by their IDs, so if they were not created in chronological order, then we need to
                # search for an active one.
                for sprint in reversed(original_value):
                    try:
                        cell_value = extract_sprint_name_from_str(sprint)
                        current_sprint = sprints[extract_sprint_id_from_str(sprint)]
                    except KeyError:
                        pass
                    else:
                        break

            if field == 'Comment':
                try:
                    # Retrieve the spillover reason.
                    cell_value = get_spillover_reason(
                        issue,
                        issue_fields,
                        current_sprint,
                        getattr(issue.fields, issue_fields['Assignee']).displayName
                    )

                    # If the reason hasn't been posted, add comment with the reminder to the issue.
                    if not cell_value and not settings.DEBUG:  # We don't want to ping people via the dev environment.
                        # Avoid circular import.
                        from sprints.dashboard.tasks import add_spillover_reminder_comment_task
                        add_spillover_reminder_comment_task.delay(
                            issue.key,
                            getattr(issue.fields, issue_fields['Assignee']).name,
                        )
                except AttributeError:
                    cell_value = 'Unassigned'

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

    # Jira orders sprints by their IDs, so if they were not created in chronological order, then we need to search for
    # an active one.
    sprint = None
    current_sprint = None
    for sprint in reversed(getattr(meetings.fields, issue_fields['Sprint'])):
        try:
            current_sprint = sprints[extract_sprint_id_from_str(sprint)]
        except KeyError:
            pass
        else:
            break

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
    column_number = _column_number_to_excel(len(spreadsheet) + 1)
    return f"'{cell_name} Commitments'!{column_number}3"


def _column_number_to_excel(column: int) -> str:
    """Convert column number to Excel-style cell name."""
    result: List[str] = []
    while column:
        column, reminder = divmod(column - 1, len(string.ascii_uppercase))
        result[:0] = string.ascii_uppercase[reminder]
    return ''.join(result)


def _get_sprint_meeting_day_division_for_member(hours: str, sprint_start: str) -> float:
    """
    Helper method for determining at which point of the member's working day is the sprint meeting.

    For invalid time format, 0 (before the working day) is assumed.
    """
    found_hours = re.findall(settings.GOOGLE_AVAILABILITY_REGEX, hours)
    try:
        start_date = parse(f"{sprint_start} {found_hours[0]}")
        end_date = parse(f"{sprint_start} {found_hours[1]}")

    except (IndexError, ParserError) as e:
        # Log exception to Sentry if the format is invalid, but do not break the server.
        if not settings.DEBUG:
            # noinspection PyUnresolvedReferences
            from sentry_sdk import capture_exception

            capture_exception(e)
        return 0

    # If availability spans two days, then adjust one end to have a real time range.
    if start_date > end_date:
        start_date -= timedelta(days=1)

    sprint_start_date = parse(f"{sprint_start} {settings.SPRINT_START_TIME_UTC}")
    available_time = (end_date - start_date).total_seconds()

    # Overlapping with sprint meeting time is going to affect the first or the last day of the sprint.
    if start_date < sprint_start_date < end_date:
        before_time = (sprint_start_date - start_date).total_seconds()
        return before_time / available_time

    return 0


def get_sprint_meeting_day_division(sprint_start: str) -> DefaultDict[str, Tuple[float, bool]]:
    """
    Returns a DefaultDict - `name : tuples with the following values:
    1. How much of the members' days is before the sprint start.
    2. Whether the member is in the positive timezone.`
    The default value is (0.0, True).

    Example:
    - 0. means that the meeting is before the user's working day,
    - 0.9 means that the meeting is in the third quarter of the user's working day
      (e.g. the member is working from 15 to 1 UTC and the meeting is at midnight).
    """
    spreadsheet = get_availability_spreadsheet()
    result: DefaultDict[str, Tuple[float, bool]] = defaultdict(lambda: (0.0, True))

    for row in spreadsheet[2:]:
        if row[0] and row[1]:
            # This could check for "+" sign, but not all fields are filled, so it's safer to assume a more popular case.
            positive_timezone = "-" not in row[2]
            result[row[0]] = (
                _get_sprint_meeting_day_division_for_member(row[1], sprint_start),
                positive_timezone,
            )
        else:
            # Ignore instructions and explanations added below the availability list.
            break

    return result


def remove_duplicates_by_attribute(lst: list, attr: str) -> list:
    """
    Remove duplicated items from a list by their attributes.

    This is a small helper for getting unique Jira resources which don't have `__eq__` and `__hash__` implemented.

    :param lst: A list of objects that contain `attr` attribute.
    :param attr: Attribute that needs to be present for each item of the `lst`.
    :return: A list of unique (by `attr`) objects.
    """
    return list({getattr(item, attr): item for item in lst}.values())
