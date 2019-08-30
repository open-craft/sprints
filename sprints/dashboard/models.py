"""These are standard Python classes, not Django models. We don't store dashboard in the DB."""

import re
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Dict,
    List,
    Set,
    Union,
)

from django.conf import settings
from jira import (
    Issue,
    User as JiraUser,
)
from jira.resources import (
    Sprint,
)

from sprints.dashboard.libs.google import (
    get_vacations,
)
from sprints.dashboard.libs.jira import (
    CustomJira,
    QuickFilter,
)
from sprints.dashboard.utils import (
    SECONDS_IN_HOUR,
    daterange,
    extract_sprint_id_from_str,
    get_all_sprints,
    get_cell_members,
    get_next_cell_sprint,
    prepare_jql_query,
    get_sprint_start_date,
    get_sprint_end_date,
    get_issue_fields,
)


class DashboardIssue:
    """Parses Jira Issue for easier access."""

    def __init__(self, issue: Issue, current_sprint_ids: Set[int], cell_members, issue_fields) -> None:
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
            self.current_sprint = extract_sprint_id_from_str(sprint) in current_sprint_ids
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

    def get_bot_directive(self, pattern) -> Union[int, None]:
        """
        Retrieves special directives placed for the Jira bot.
        :returns `None` if directive was not found. Otherwise returns `int` with duration defined in the directive.
        """
        try:
            search = re.search(pattern, self.description)
            return int(search.group(1))  # type: ignore
        except (AttributeError, TypeError):
            # Directive not found or description is `None`.
            return None

    def calculate_review_time(self) -> int:
        """
        Calculate time needed for the review.
        Unless directly specified (with Jira bot directive), we're planning 2 hours for stories bigger than 3 points.
        """
        try:
            planned = self.get_bot_directive(settings.SPRINT_REVIEW_DIRECTIVE)
            return planned * SECONDS_IN_HOUR  # type: ignore

        except TypeError:
            if self.story_points <= 3:
                return SECONDS_IN_HOUR
            return 2 * SECONDS_IN_HOUR

    def get_recurring_time(self) -> int:
        """Get required assignee time for the recurring story."""
        planned = self.get_bot_directive(settings.SPRINT_RECURRING_DIRECTIVE) or 0
        return planned * SECONDS_IN_HOUR

    def get_epic_management_time(self) -> int:
        """Get required assignee time for managing the epic."""
        try:
            planned = self.get_bot_directive(settings.SPRINT_EPIC_DIRECTIVE)
            return planned * SECONDS_IN_HOUR  # type: ignore
        except TypeError:
            return settings.SPRINT_HOURS_RESERVED_FOR_EPIC_MANAGEMENT * SECONDS_IN_HOUR


class DashboardRow:
    """Represents single dashboard row (user)."""

    def __init__(self, user: Union[JiraUser, str, None]) -> None:
        super().__init__()
        self.user = user
        self.current_remaining_assignee_time = 0
        self.current_remaining_review_time = 0
        self.current_remaining_upstream_time = 0
        self.future_remaining_assignee_time = 0
        self.future_remaining_review_time = 0
        self.future_epic_management_time = 0
        self.goal_time = 0
        self.current_unestimated: List[str] = []
        self.future_unestimated: List[str] = []
        self.vacation_time = 0

    def set_goal_time(self, goal) -> None:
        """
        Calculate goal time for this user.
        Use default if time not specified in user's profile.
        """
        self.goal_time = goal - settings.SPRINT_HOURS_RESERVED_FOR_MEETINGS * SECONDS_IN_HOUR

    @property
    def committed_time(self) -> float:
        """Calculate summary time for the upcoming sprint."""
        return (self.current_remaining_assignee_time
                + self.current_remaining_review_time
                + self.current_remaining_upstream_time
                + self.future_remaining_assignee_time
                + self.future_remaining_review_time
                + self.future_epic_management_time)

    @property
    def remaining_time(self) -> float:
        """Calculate available time for the upcoming sprint."""
        return self.goal_time - self.committed_time

    def __eq__(self, other) -> bool:
        if isinstance(other, JiraUser):
            return self.user == other
        return self.user == other.user

    def add_unestimated_issue(self, issue: DashboardIssue) -> None:
        """Add non-estimated issue to the list of unestimated issues."""
        if issue.current_sprint:
            self.current_unestimated.append(issue.key)
        else:
            self.future_unestimated.append(issue.key)


class Dashboard:
    """Aggregates user records into a dashboard."""

    def __init__(self, board_id: int, conn: CustomJira) -> None:
        super().__init__()
        self.jira_connection = conn
        self.dashboard: Dict[Union[JiraUser, str, None], DashboardRow] = {}
        self.issue_fields: Dict[str, str]
        self.issues: List[DashboardIssue]
        self.members: List[str]
        self.commitments: Dict[str, Dict[str, Union[int, Dict[str, str]]]] = {}
        self.board_id = board_id
        self.active_sprints: List[Sprint]
        self.cell_future_sprint: Sprint
        self.future_sprints: List[Sprint]
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
        sprints = get_all_sprints(self.jira_connection)
        self.active_sprints = sprints['active']
        self.future_sprints = sprints['future']

        for sprint in self.future_sprints:
            if sprint.originBoardId == self.board_id:
                self.cell_future_sprint = sprint
                break

        self.future_sprint_start = get_sprint_start_date(self.future_sprints[0])
        self.future_sprint_end = get_sprint_end_date(self.future_sprints[0], sprints['all'])

    def get_issues(self) -> None:
        """Retrieves all stories and epics for the current dashboard."""
        self.issue_fields = get_issue_fields(self.jira_connection, settings.JIRA_REQUIRED_FIELDS)

        issues: List[Issue] = self.jira_connection.search_issues(
            **prepare_jql_query(
                [str(sprint.id) for sprint in self.active_sprints + self.future_sprints],
                list(self.issue_fields.values())
            ),
            maxResults=0,
        )
        quickfilters: List[QuickFilter] = self.jira_connection.quickfilters(self.board_id)

        self.members = get_cell_members(quickfilters)
        self.issues = []

        active_sprint_ids = {sprint.id for sprint in self.active_sprints}
        for issue in issues:
            self.issues.append(DashboardIssue(issue, active_sprint_ids, self.members, self.issue_fields))

        for member in self.members:
            schedule = self.jira_connection.user_schedule(
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
            if issue.status == settings.SPRINT_STATUS_RECURRING:
                assignee.future_remaining_assignee_time += issue.get_recurring_time()
                continue

            # Check if the issue has any time left.
            if issue.time_estimate == 0 and isinstance(issue.assignee, JiraUser):
                assignee.add_unestimated_issue(issue)

            # Calculations for the current sprint.
            if issue.current_sprint:
                # Assume that no more review will be needed at this point.
                if issue.status == settings.SPRINT_STATUS_EXTERNAL_REVIEW:
                    assignee.current_remaining_upstream_time += issue.time_estimate

                # Assume that no more reviews will be needed at this point.
                elif issue.status == settings.SPRINT_STATUS_MERGED:
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
                            max(vacation['start']['date'], self.future_sprint_start),  # type: ignore
                            min(vacation['end']['date'], self.future_sprint_end),  # type: ignore
                        ):
                            row.vacation_time += self.commitments[row.user.name]['days'][vacation_date]  # type: ignore
                    elif row.user.displayName < vacation['user']:
                        # Small optimization, as users' vacations are sorted.
                        break

                row.set_goal_time(self.commitments[row.user.name]['total'] - row.vacation_time)
