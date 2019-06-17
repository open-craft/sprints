import re
from contextlib import contextmanager
from typing import ContextManager, Dict, List

from jira import JIRA
# noinspection PyProtectedMember
from jira.resources import Board, GreenHopperResource, Issue, Sprint, User as JiraUser

from config.settings.base import JIRA_CUSTOM_FIELDS, JIRA_PASSWORD, JIRA_REQUIRED_FIELDS, JIRA_SERVER, \
    JIRA_SPRINT_BOARD_PREFIX, JIRA_USERNAME, SPRINT_DEFAULT_COMMITMENT, SPRINT_EPIC_DIRECTIVE, \
    SPRINT_HOURS_RESERVED_FOR_MEETINGS, SPRINT_RECURRING_DIRECTIVE, SPRINT_REVIEW_DIRECTIVE, \
    SPRINT_STATUS_EPIC_IN_PROGRESS, SPRINT_STATUS_EXTERNAL_REVIEW, SPRINT_STATUS_MERGED, SPRINT_STATUS_RECURRING, \
    SPRINT_STATUS_UNFINISHED
from sprints.users.models import User

SECONDS_IN_HOUR = 3600


@contextmanager
def connect_to_jira() -> ContextManager[JIRA]:
    """Context manager for establishing connection with Jira server."""
    conn = JIRA(
        server=JIRA_SERVER,
        basic_auth=(JIRA_USERNAME, JIRA_PASSWORD),
        options={'agile_rest_path': GreenHopperResource.AGILE_BASE_REST_PATH}
    )
    yield conn
    conn.close()


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


def get_active_sprint(board_id: int) -> Sprint:
    """Get active sprint for the selected board."""
    with connect_to_jira() as conn:
        return conn.sprints(board_id, state='active')[0]


def prepare_jql_query(project: str, current_sprint: int) -> Dict[str, str]:
    """Prepare JQL query for retrieving stories and epics for the selected cell for the current and upcoming sprint."""
    unfinished_status = '"' + '","'.join(SPRINT_STATUS_UNFINISHED | {SPRINT_STATUS_RECURRING}) + '"'
    epic_in_progress = '"' + '","'.join(SPRINT_STATUS_EPIC_IN_PROGRESS) + '"'

    query = f'project={project} AND ((Sprint IN {(current_sprint, current_sprint + 1)} and ' \
        f'status IN ({unfinished_status})) OR (issuetype = Epic AND Status IN ({epic_in_progress})))'
    fields = JIRA_REQUIRED_FIELDS

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
    result = re.search(pattern, sprint_str).group(1)
    return result


class DashboardIssue:
    """Parses Jira Issue for easier access."""

    def __init__(self, issue: Issue, current_sprint_id) -> None:
        super().__init__()
        self.key = issue.key
        # It should be present, but that's not enforced by the library, so it's better to specify default value.
        self.assignee = getattr(issue.fields, 'assignee', None)
        self.description = getattr(issue.fields, 'description', '')
        self.status = getattr(issue.fields, 'status').name
        self.time_spent = getattr(issue.fields, 'timespent', 0) or 0
        self.time_estimate = getattr(issue.fields, 'timeestimate', 0) or 0
        self.is_epic = getattr(issue.fields, 'issuetype').name == 'Epic'

        try:
            sprint = getattr(issue.fields, JIRA_CUSTOM_FIELDS['sprint'])
            if isinstance(sprint, list):
                sprint = sprint[0]
            self.current_sprint = extract_sprint_id_from_str(sprint) == current_sprint_id
        except (AttributeError, TypeError):
            # Possible for epics
            self.current_sprint = False
        try:
            self.story_points = int(getattr(issue.fields, JIRA_CUSTOM_FIELDS['story_points'], 0))
        except (AttributeError, TypeError):
            self.story_points = 0
        self.reviewer_1: JiraUser = getattr(issue.fields, JIRA_CUSTOM_FIELDS['reviewer_1'], None)
        # self.reviewer_2: JiraUser = getattr(issue.fields, JIRA_CUSTOM_FIELDS['reviewer_2'], None)

        self.review_time = self.calculate_review_time()

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
        return planned * SECONDS_IN_HOUR


class DashboardRow:
    """Represents single dashboard row (user)."""

    def __init__(self, user: JiraUser) -> None:
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

    @property
    def goal_time(self) -> int:
        """
        Calculate goal time for this user.
        Use default if time not specified in user's profile.
        """
        try:
            goal = self.local_user.goal
        except AttributeError:
            goal = SPRINT_DEFAULT_COMMITMENT
        return goal - SPRINT_HOURS_RESERVED_FOR_MEETINGS

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
        """TODO"""
        # Check if current or future sprint.
        ...


class Dashboard:
    """Aggregates user records into a dashboard."""

    def __init__(self, project: str, sprint: Sprint) -> None:
        super().__init__()
        self.dashboard: Dict[JiraUser, DashboardRow] = {}
        self.issues = List[DashboardIssue]
        self.project = project
        self.sprint = sprint
        self.future_sprint_name = None
        self.get_issues()
        self.generate_rows()

    @property
    def rows(self):
        """Simplification for the serializer."""
        return self.dashboard.values()

    def get_issues(self) -> None:
        """Retrieves all stories and epics for the current dashboard."""
        with connect_to_jira() as conn:
            issues: List[Issue] = conn.search_issues(**prepare_jql_query(self.project, self.sprint.id), maxResults=0)

        self.issues = []

        for issue in issues:
            self.issues.append(DashboardIssue(issue, self.sprint.id))

            # Hack to limit external requests to Jira.
            if not self.future_sprint_name and not self.issues[-1].current_sprint:
                try:
                    sprint = getattr(issue.fields, JIRA_CUSTOM_FIELDS['sprint'])
                    if isinstance(sprint, list):
                        sprint = sprint[0]
                    self.future_sprint_name = extract_sprint_name_from_str(sprint)
                except (AttributeError, TypeError):
                    # Possible for epics
                    pass

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
            if issue.time_estimate == 0:
                assignee.add_invalid_issue(issue)
                continue

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
                    assignee.current_remaining_assignee_time += max(issue.time_estimate - issue.review_time, 0)

            # Calculations for the upcoming sprint.
            else:
                assignee.future_remaining_assignee_time += issue.time_estimate
                reviewer_1.future_remaining_review_time += issue.review_time
