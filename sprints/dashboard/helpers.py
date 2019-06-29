import re
from contextlib import contextmanager
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    ContextManager,
    Dict,
    Generator,
    List,
    Union,
)

# noinspection PyProtectedMember
from google.oauth2 import service_account
from googleapiclient import discovery
from jira.resources import (
    Board,
    GreenHopperResource,
    Issue,
    Sprint,
    User as JiraUser,
)

from config.settings.base import (
    GOOGLE_API_CREDENTIALS,
    GOOGLE_CALENDAR_VACATION_REGEX,
    JIRA_BOARD_QUICKFILTER_PATTERN,
    JIRA_PASSWORD,
    JIRA_REQUIRED_FIELDS,
    JIRA_SERVER,
    JIRA_SPRINT_BOARD_PREFIX,
    JIRA_USERNAME,
    SPRINT_DATE_REGEX,
    SPRINT_EPIC_DIRECTIVE,
    SPRINT_HOURS_RESERVED_FOR_EPIC_MANAGEMENT,
    SPRINT_HOURS_RESERVED_FOR_MEETINGS,
    SPRINT_NUMBER_REGEX,
    SPRINT_RECURRING_DIRECTIVE,
    SPRINT_REVIEW_DIRECTIVE,
    SPRINT_STATUS_EPIC_IN_PROGRESS,
    SPRINT_STATUS_EXTERNAL_REVIEW,
    SPRINT_STATUS_MERGED,
    SPRINT_STATUS_RECURRING,
    SPRINT_STATUS_UNFINISHED,
)
from sprints.dashboard.api import (
    CustomJira,
    QuickFilter,
)
from sprints.users.models import User

SECONDS_IN_HOUR = 3600


@contextmanager
def connect_to_jira() -> ContextManager[CustomJira]:
    """Context manager for establishing connection with Jira server."""
    conn = CustomJira(
        server=JIRA_SERVER,
        basic_auth=(JIRA_USERNAME, JIRA_PASSWORD),
        options={'agile_rest_path': GreenHopperResource.AGILE_BASE_REST_PATH}
    )
    yield conn
    conn.close()


@contextmanager
def connect_to_google() -> ContextManager[discovery.Resource]:
    """Connects to Google API with service account."""
    scopes = ['https://www.googleapis.com/auth/calendar']
    credentials = service_account.Credentials.from_service_account_info(GOOGLE_API_CREDENTIALS, scopes=scopes)
    service = discovery.build('calendar', 'v3', credentials=credentials)
    yield service


def get_vacations(from_: str, to: str) -> List[Dict[str, Union[str, Dict[str, str]]]]:
    """Retrieves user's vacations from Google Calendar."""
    with connect_to_google() as conn:
        calendars = [item['id'] for item in conn.calendarList().list(fields='items(id)').execute()['items']]
        vacations = []
        for calendar in calendars:
            events = conn.events().list(
                calendarId=calendar,
                timeZone='Europe/London',
                timeMin=f'{from_}T00:00:00Z',
                timeMax=f'{to}T00:00:00Z',
                fields='items(end/date, start/date, summary)'
            ).execute()

            for event in events['items']:
                try:
                    user = re.match(GOOGLE_CALENDAR_VACATION_REGEX, event['summary']).group(1)
                    del event['summary']
                    event['user'] = user
                    vacations.append(event)
                except AttributeError:
                    # Ignore non-matching events.
                    pass

        vacations.sort(key=lambda x: x['user'])  # Small optimization for searching
        return vacations


class Cell:
    """Model representing cell - its name and sprint board ID."""
    pattern = fr'{JIRA_SPRINT_BOARD_PREFIX}(.*)'

    def __init__(self, board: Board) -> None:
        super().__init__()
        self.name = re.search(self.pattern, board.name).group(1)
        self.board_id = board.id


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


def daterange(start: str, end: str) -> Generator[str, None, None]:
    """Generates days from `start_date` to `end_date` (both inclusive)."""
    start_date = datetime.strptime(start, '%Y-%m-%d')
    end_date = datetime.strptime(end, '%Y-%m-%d')
    for n in range(int((end_date - start_date).days + 1)):
        yield (start_date + timedelta(n)).strftime('%Y-%m-%d')


class DashboardIssue:
    """Parses Jira Issue for easier access."""

    def __init__(self, issue: Issue, current_sprint_id, cell_members, issue_fields) -> None:
        super().__init__()
        self.key = issue.key
        # It should be present, but that's not enforced by the library, so it's better to specify default value.
        self.assignee = getattr(issue.fields, issue_fields['Assignee'], None)
        # We don't want to treat commitments from the other cell as "Unassigned".
        if self.assignee and self.assignee.name not in cell_members:
            self.assignee = "Other Cell"
        self.description = getattr(issue.fields, issue_fields['Description'], '')
        self.status = getattr(issue.fields, issue_fields['Status']).name
        self.time_spent = getattr(issue.fields, issue_fields['Time Spent'], 0) or 0
        self.time_estimate = getattr(issue.fields, issue_fields['Remaining Estimate'], 0) or 0
        self.is_epic = getattr(issue.fields, issue_fields['Issue Type']).name == 'Epic'

        try:
            sprint = getattr(issue.fields, issue_fields['Sprint'])
            if isinstance(sprint, list):
                sprint = sprint[-1]
            self.current_sprint = extract_sprint_id_from_str(sprint) == current_sprint_id
        except (AttributeError, TypeError):
            # Possible for epics
            self.current_sprint = False
        try:
            self.story_points = int(getattr(issue.fields, issue_fields['Story Points'], 0))
        except (AttributeError, TypeError):
            self.story_points = 0
        self.reviewer_1: JiraUser = getattr(issue.fields, issue_fields['Reviewer 1'], None)
        # We don't want to treat commitments from the other cell as "Unassigned".
        if self.reviewer_1 and self.reviewer_1.name not in cell_members:
            self.reviewer_1 = "Other Cell"

        self.review_time = self.calculate_review_time()
        self.assignee_time = max(self.time_estimate - self.review_time, 0)  # We don't want negative values here

    def get_bot_directive(self, pattern) -> int:
        """Retrieves special directives placed for the Jira bot."""
        try:
            return int(re.search(pattern, self.description).group(1))
        except (IndexError, AttributeError, TypeError):
            return 0

    def calculate_review_time(self) -> int:
        """
        Calculate time needed for the review.
        Unless directly specified (with Jira bot directive), we're planning 2 hours for stories bigger than 3 points.
        """
        planned = self.get_bot_directive(SPRINT_REVIEW_DIRECTIVE)
        if planned:
            return planned * SECONDS_IN_HOUR

        if self.story_points <= 3:
            return SECONDS_IN_HOUR
        return 2 * SECONDS_IN_HOUR

    def get_recurring_time(self) -> int:
        """Get required assignee time for the recurring story."""
        planned = self.get_bot_directive(SPRINT_RECURRING_DIRECTIVE)
        return planned * SECONDS_IN_HOUR

    def get_epic_management_time(self) -> int:
        """Get required assignee time for managing the epic."""
        planned = self.get_bot_directive(SPRINT_EPIC_DIRECTIVE)
        return planned * SECONDS_IN_HOUR or SPRINT_HOURS_RESERVED_FOR_EPIC_MANAGEMENT * SECONDS_IN_HOUR


class DashboardRow:
    """Represents single dashboard row (user)."""

    def __init__(self, user: Union[JiraUser, str, None]) -> None:
        super().__init__()
        self.user = user
        try:
            self.local_user = User.objects.get(email=self.user.emailAddress)
        except (User.DoesNotExist, AttributeError):
            self.local_user = None
        self.current_remaining_assignee_time = 0
        self.current_remaining_review_time = 0
        self.current_remaining_upstream_time = 0
        self.future_remaining_assignee_time = 0
        self.future_remaining_review_time = 0
        self.future_epic_management_time = 0
        self.goal_time = 0
        self.current_invalid = []
        self.future_invalid = []
        self.vacation_time = 0

    def set_goal_time(self, goal) -> None:
        """
        Calculate goal time for this user.
        Use default if time not specified in user's profile.
        """
        self.goal_time = goal - SPRINT_HOURS_RESERVED_FOR_MEETINGS * SECONDS_IN_HOUR

    @property
    def committed_time(self) -> float:
        """Calculate summary time for the upcoming sprint."""
        return self.current_remaining_assignee_time \
               + self.current_remaining_review_time \
               + self.current_remaining_upstream_time \
               + self.future_remaining_assignee_time \
               + self.future_remaining_review_time \
               + self.future_epic_management_time

    @property
    def remaining_time(self) -> float:
        """Calculate available time for the upcoming sprint."""
        return self.goal_time - self.committed_time

    def __eq__(self, other) -> bool:
        if isinstance(other, JiraUser):
            return self.user == other
        return self.user == other.user

    def add_invalid_issue(self, issue: DashboardIssue) -> None:
        """Add non-estimated issue to the list of invalid issues."""
        if issue.current_sprint:
            self.current_invalid.append(issue.key)
        else:
            self.future_invalid.append(issue.key)


class Dashboard:
    """Aggregates user records into a dashboard."""

    def __init__(self, board_id: int) -> None:
        super().__init__()
        self.dashboard: Dict[Union[JiraUser, str, None], DashboardRow] = {}
        self.issue_fields: Dict[str, str]
        self.issues: List[DashboardIssue]
        self.members: List[str]
        self.commitments: Dict[str, Dict[str, Union[int, Dict[str, str]]]] = {}
        self.board_id = board_id
        self.sprint: Sprint
        self.future_sprint: Sprint
        self.future_sprint_start: str
        self.future_sprint_end: str

        # Retrieve data from Jira.
        self.get_sprints()
        self.vacations = get_vacations(self.future_sprint_start, self.future_sprint_end)
        self.get_issues()
        self.generate_rows()

    @property
    def rows(self):
        """Simplification for the serializer."""
        return self.dashboard.values()

    def get_sprints(self) -> None:
        """Retrieves current and future sprint for the board."""
        with connect_to_jira() as conn:
            sprints: List[Sprint] = conn.sprints(self.board_id, state='active, future')

        for sprint in sprints:
            if sprint.name.startswith('Sprint') and sprint.state == 'active':
                self.sprint = sprint
                break

        self.future_sprint = find_next_sprint(sprints, self.sprint)
        self.future_sprint_start = re.search(SPRINT_DATE_REGEX, self.future_sprint.name).group(1)

        next_future_sprint = find_next_sprint(sprints, self.future_sprint)
        next_future_sprint_start = re.search(SPRINT_DATE_REGEX, next_future_sprint.name).group(1)
        end_date = datetime.strptime(next_future_sprint_start, '%Y-%m-%d') - timedelta(days=1)
        self.future_sprint_end = end_date.strftime('%Y-%m-%d')

    def get_issues(self) -> None:
        """Retrieves all stories and epics for the current dashboard."""
        with connect_to_jira() as conn:
            field_ids = {field['name']: field['id'] for field in conn.fields()}
            self.issue_fields = {field: field_ids[field] for field in JIRA_REQUIRED_FIELDS}

            issues: List[Issue] = conn.search_issues(
                **prepare_jql_query(
                    self.sprint.id,
                    self.future_sprint.id,
                    list(self.issue_fields.values())
                ),
                maxResults=0,
            )
            quickfilters: List[QuickFilter] = conn.quickfilters(self.board_id)

            self.members = get_cell_members(quickfilters)
            self.issues = []

            for issue in issues:
                self.issues.append(DashboardIssue(issue, self.sprint.id, self.members, self.issue_fields))

            for member in self.members:
                schedule = conn.user_schedule(
                    member,
                    self.future_sprint_start,
                    self.future_sprint_end,
                )
                self.commitments[member] = {
                    'total': schedule.requiredSeconds,
                    'days': {day.date: day.requiredSeconds for day in schedule.days}
                }

    def generate_rows(self) -> None:
        """Generates rows for all users and calculates their time stats."""
        for issue in self.issues:  # type: DashboardIssue
            assignee = self.dashboard.setdefault(issue.assignee, DashboardRow(issue.assignee))
            reviewer_1 = self.dashboard.setdefault(issue.reviewer_1, DashboardRow(issue.reviewer_1))

            # Calculate time for epic management
            if issue.is_epic:
                assignee.future_epic_management_time += issue.get_epic_management_time()
                continue

            # Calculate hours for recurring tickets for the upcoming sprint.
            if issue.status == SPRINT_STATUS_RECURRING:
                assignee.future_remaining_assignee_time += issue.get_recurring_time()
                continue

            # Check if the issue has any time left.
            if issue.time_estimate == 0 and isinstance(issue.assignee, JiraUser):
                assignee.add_invalid_issue(issue)

            # Calculations for the current sprint.
            if issue.current_sprint:
                # Assume that no more review will be needed at this point.
                if issue.status == SPRINT_STATUS_EXTERNAL_REVIEW:
                    assignee.current_remaining_upstream_time += issue.time_estimate

                # Assume that no more reviews will be needed at this point.
                elif issue.status == SPRINT_STATUS_MERGED:
                    assignee.current_remaining_assignee_time += issue.time_estimate

                else:
                    reviewer_1.current_remaining_review_time += issue.review_time
                    assignee.current_remaining_assignee_time += issue.assignee_time

            # Calculations for the upcoming sprint.
            else:
                assignee.future_remaining_assignee_time += issue.assignee_time
                reviewer_1.future_remaining_review_time += issue.review_time

        del self.dashboard['Other Cell']

        # Calculate commitments for each user.
        for row in self.rows:
            if isinstance(row.user, JiraUser):
                # Calculate vacations
                for vacation in self.vacations:
                    if row.user.displayName.startswith(vacation['user']):
                        for vacation_date in daterange(
                            max(vacation['start']['date'], self.future_sprint_start),
                            min(vacation['end']['date'], self.future_sprint_end),
                        ):
                            row.vacation_time += self.commitments[row.user.name]['days'][vacation_date]
                    elif row.user.displayName < vacation['user']:
                        # Small optimization, as users' vacations are sorted.
                        break

                row.set_goal_time(self.commitments[row.user.name]['total'] - row.vacation_time)
