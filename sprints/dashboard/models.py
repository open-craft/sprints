"""These are standard Python classes, not Django models. We don't store dashboard in the DB."""
import functools
import re
from typing import (
    Dict,
    List,
    Set,
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
    SECONDS_IN_MINUTE,
    daterange,
    extract_sprint_id_from_str,
    get_all_sprints,
    get_cell_members,
    get_issue_fields,
    get_sprint_end_date,
    get_sprint_meeting_day_division,
    get_sprint_start_date,
    prepare_jql_query,
)


class DashboardIssue:
    """Parses Jira Issue for easier access."""

    def __init__(
        self,
        issue: Issue,
        current_sprint_ids: Set[int],
        cell_members: List[str],
        unassigned_user: JiraUser,
        other_cell: JiraUser,
        issue_fields: Dict[str, str],
    ) -> None:
        self.key = issue.key
        # It should be present, but that's not enforced by the library, so it's better to specify default value.
        self.assignee: JiraUser = getattr(issue.fields, issue_fields['Assignee'], None)
        if not self.assignee:
            self.assignee = unassigned_user
        # We don't want to treat commitments from the other cell as "Unassigned".
        elif self.assignee.name not in cell_members:
            self.assignee = other_cell

        self.summary = getattr(issue.fields, issue_fields['Summary'], '')
        self.description = getattr(issue.fields, issue_fields['Description'], '')
        self.status = getattr(issue.fields, issue_fields['Status']).name
        self.time_spent = getattr(issue.fields, issue_fields['Time Spent'], 0) or 0
        self.time_estimate = getattr(issue.fields, issue_fields['Remaining Estimate'], 0) or 0
        self.is_epic = getattr(issue.fields, issue_fields['Issue Type']).name == 'Epic'
        self.account = getattr(issue.fields, issue_fields['Account']).name

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
        self.reviewer_1: JiraUser = getattr(issue.fields, issue_fields['Reviewer 1'], "Unassigned")
        if not self.reviewer_1:
            self.reviewer_1 = unassigned_user
        # We don't want to treat commitments from the other cell as "Unassigned".
        elif self.reviewer_1.name not in cell_members:
            self.reviewer_1 = other_cell

    def get_bot_directive(self, pattern) -> int:
        """
        Retrieves time (in seconds) specified with special directives placed for the Jira bot in ticket's description.
        :returns `int` with duration (converted to seconds) defined with the directive.
        :raises `ValueError` if directive was not found.
        """
        try:
            search = re.search(pattern, self.description).groupdict('0')  # type: ignore
            hours = int(search.get('hours', 0))
            minutes = int(search.get('minutes', 0))
            print(hours, minutes)
            return hours * SECONDS_IN_HOUR + minutes * SECONDS_IN_MINUTE
        except (AttributeError, TypeError):  # Directive not found or description is `None`.
            raise ValueError

    @property  # type: ignore  # cf: https://github.com/python/mypy/issues/1362
    @functools.lru_cache()  # We'll need to use ignore for `return` (cf: https://github.com/python/mypy/issues/5858)
    def assignee_time(self) -> int:
        """Calculate time needed by the assignee of the issue."""
        if self.is_epic:
            return 0

        # Assume that no more review will be needed at this point.
        if self.status in (settings.SPRINT_STATUS_EXTERNAL_REVIEW, settings.SPRINT_STATUS_MERGED):
            return self.time_estimate

        return max(self.time_estimate - self.review_time, 0)  # We don't want negative values here.

    @property  # type: ignore  # cf: https://github.com/python/mypy/issues/1362
    @functools.lru_cache()
    def review_time(self) -> int:
        """
        Calculate time needed for the review.
        Unless directly specified (with Jira bot directive), we're planning 2 hours for stories bigger than 3 points.
        """
        # Assume that no more review will be needed at this point
        # (unless specified with SPRINT_REVIEW_REMAINING_DIRECTIVE).
        if self.status in (settings.SPRINT_STATUS_EXTERNAL_REVIEW, settings.SPRINT_STATUS_MERGED):
            try:
                return self.get_bot_directive(settings.SPRINT_REVIEW_REMAINING_DIRECTIVE)
            except ValueError:
                return 0

        try:
            return self.get_bot_directive(settings.SPRINT_REVIEW_DIRECTIVE)

        except ValueError:
            # If we want to plan review time for epic or recurring issue, we need to specify it with bot's directive.
            if self.is_epic or self.status == settings.SPRINT_STATUS_RECURRING:
                return 0

            if self.story_points <= 3:
                return SECONDS_IN_HOUR
            return int(2 * SECONDS_IN_HOUR)

    @property  # type: ignore  # cf: https://github.com/python/mypy/issues/1362
    @functools.lru_cache()
    def recurring_time(self) -> int:
        """Get required assignee time for the recurring story."""
        if self.status == settings.SPRINT_STATUS_RECURRING:
            try:
                return self.get_bot_directive(settings.SPRINT_RECURRING_DIRECTIVE)
            except ValueError:  # Directive not found.
                pass
        return 0

    @property  # type: ignore  # cf: https://github.com/python/mypy/issues/1362
    @functools.lru_cache()
    def epic_management_time(self) -> int:
        """Get required assignee time for managing the epic."""
        if not self.is_epic:
            return 0

        try:
            return self.get_bot_directive(settings.SPRINT_EPIC_DIRECTIVE)
        except ValueError:
            return settings.SPRINT_HOURS_RESERVED_FOR_EPIC_MANAGEMENT * SECONDS_IN_HOUR


class DashboardRow:
    """Represents single dashboard row (user)."""

    def __init__(self, user: JiraUser) -> None:
        self.user = user
        self.current_remaining_assignee_time = 0
        self.current_remaining_review_time = 0
        self.current_remaining_upstream_time = 0
        self.future_assignee_time = 0
        self.future_review_time = 0
        self.future_epic_management_time = 0
        self.goal_time = 0
        self.current_unestimated: List[str] = []
        self.future_unestimated: List[str] = []
        self.vacation_time = 0.
        # self.issues: List[DashboardIssue] = []

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
                + self.future_assignee_time
                + self.future_review_time
                + self.future_epic_management_time)

    @property
    def remaining_time(self) -> float:
        """Calculate available time for the upcoming sprint."""
        return self.goal_time - self.committed_time

    def add_unestimated_issue(self, issue: DashboardIssue) -> None:
        """Add non-estimated issue to the list of unestimated issues."""
        if issue.current_sprint:
            self.current_unestimated.append(issue.key)
        else:
            self.future_unestimated.append(issue.key)


class Dashboard:
    """Aggregates user records into a dashboard."""

    def __init__(self, board_id: int, conn: CustomJira) -> None:
        self.jira_connection = conn
        self.dashboard: Dict[JiraUser, DashboardRow] = {}
        self.issue_fields: Dict[str, str]
        self.issues: List[DashboardIssue]
        self.members: List[str]
        self.commitments: Dict[str, Dict[str, Dict[str, int]]] = {}
        self.board_id = board_id
        self.active_sprints: List[Sprint]
        self.cell_future_sprint: Sprint
        self.future_sprints: List[Sprint]
        self.future_sprint_start: str
        self.future_sprint_end: str

        # Retrieve data from Jira.
        self.get_sprints()
        self.create_mock_users()
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

        self.future_sprint_start = get_sprint_start_date(self.cell_future_sprint)
        self.future_sprint_end = get_sprint_end_date(self.cell_future_sprint, sprints['all'])

    def create_mock_users(self):
        """Create mock users for handling unassigned and cross-cell tickets."""
        self.unassigned_user = JiraUser(self.jira_connection._options, self.jira_connection._session)
        self.unassigned_user.name = "Unassigned"
        self.unassigned_user.displayName = self.unassigned_user.name

        # We don't want to treat commitments from the other cell as "Unassigned".
        self.other_cell = JiraUser(self.jira_connection._options, self.jira_connection._session)
        self.other_cell.name = "Other Cell"
        self.other_cell.displayName = "Other Cell"

    def delete_mock_users(self) -> None:
        """Remove mock users from the dashboard. It's useful for exporting commitments."""
        self.dashboard.pop(self.other_cell, None)
        self.dashboard.pop(self.unassigned_user, None)

    def get_issues(self) -> None:
        """Retrieves all stories and epics for the current dashboard."""
        self.issue_fields = get_issue_fields(self.jira_connection, settings.JIRA_REQUIRED_FIELDS)

        issues: List[Issue] = self.jira_connection.search_issues(
            **prepare_jql_query(
                [str(sprint.id) for sprint in self.active_sprints + self.future_sprints],
                list(self.issue_fields.values()),
            ),
            maxResults=0,
        )
        quickfilters: List[QuickFilter] = self.jira_connection.quickfilters(self.board_id)

        self.members = get_cell_members(quickfilters)
        self.sprint_division = get_sprint_meeting_day_division()
        self.issues = []

        active_sprint_ids = {sprint.id for sprint in self.active_sprints}
        for issue in issues:
            self.issues.append(
                DashboardIssue(issue, active_sprint_ids, self.members, self.unassigned_user, self.other_cell,
                               self.issue_fields))

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
                assignee.future_epic_management_time += issue.epic_management_time  # type: ignore
                continue

            # Calculate hours for recurring tickets for the upcoming sprint.
            if issue.status == settings.SPRINT_STATUS_RECURRING:
                assignee.future_assignee_time += issue.recurring_time  # type: ignore
                reviewer_1.future_review_time += issue.review_time  # type: ignore
                continue

            # Check if the issue has any time left.
            if issue.time_estimate == 0 and issue.assignee not in (self.unassigned_user, self.other_cell):
                assignee.add_unestimated_issue(issue)

            # Calculations for the current sprint.
            if issue.current_sprint:
                # Assume that no more review will be needed at this point.
                if issue.status == settings.SPRINT_STATUS_EXTERNAL_REVIEW:
                    assignee.current_remaining_upstream_time += issue.assignee_time  # type: ignore

                else:
                    reviewer_1.current_remaining_review_time += issue.review_time  # type: ignore
                    assignee.current_remaining_assignee_time += issue.assignee_time  # type: ignore

            # Calculations for the upcoming sprint.
            else:
                assignee.future_assignee_time += issue.assignee_time  # type: ignore
                reviewer_1.future_review_time += issue.review_time  # type: ignore

        self.dashboard.pop(self.other_cell, None)

        # Calculate commitments for each user.
        for row in self.rows:
            if row.user != self.unassigned_user:
                # Calculate vacations
                for vacation in self.vacations:
                    if row.user.displayName.startswith(vacation['user']):
                        for vacation_date in daterange(
                            max(vacation['start']['date'], self.future_sprint_start),  # type: ignore
                            min(vacation['end']['date'], self.future_sprint_end),  # type: ignore
                        ):
                            # Special cases for partial day when the sprint starts/ends.
                            if vacation_date == self.future_sprint_start:
                                row.vacation_time += \
                                    self.commitments[row.user.name]['days'][vacation_date] * \
                                    (1 - self.sprint_division[row.user.displayName])
                            elif vacation_date == self.future_sprint_end:
                                row.vacation_time += \
                                    self.commitments[row.user.name]['days'][vacation_date] * \
                                    self.sprint_division[row.user.displayName]
                            else:
                                row.vacation_time += \
                                    self.commitments[row.user.name]['days'][vacation_date]
                    elif row.user.displayName < vacation['user']:
                        # Small optimization, as users' vacations are sorted.
                        break

                # noinspection PyTypeChecker
                row.set_goal_time(self.commitments[row.user.name]['total'] - row.vacation_time)
