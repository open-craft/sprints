"""These are standard Python classes, not Django models. We don't store dashboard in the DB."""
import functools
import re
import typing
from datetime import timedelta
from typing import (
    Dict,
    List,
    Set,
)

from dateutil.parser import parse
from django.conf import settings
from jira import (
    Issue,
    User as JiraUser,
)
from jira.resources import Sprint

from config.settings.base import (
    SECONDS_IN_HOUR,
    SECONDS_IN_MINUTE,
)
from sprints.dashboard.libs.google import get_vacations
from sprints.dashboard.libs.jira import (
    CustomJira,
    QuickFilter,
)
from sprints.dashboard.utils import (
    daterange,
    extract_sprint_id_from_str,
    get_all_sprints,
    get_cell_key,
    get_cell_members,
    get_issue_fields,
    get_next_sprint,
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
        cell_key: str,
    ) -> None:
        self.key = issue.key
        # It should be present, but that's not enforced by the library, so it's better to specify default value.
        self.assignee: JiraUser = getattr(issue.fields, issue_fields['Assignee'], None)
        # We don't want to treat commitments from the other cell as "Unassigned".
        if not self.key.startswith(cell_key):
            self.assignee = other_cell
        elif not self.assignee:
            self.assignee = unassigned_user

        self.summary = getattr(issue.fields, issue_fields['Summary'], '')
        self.description = getattr(issue.fields, issue_fields['Description'], '')
        self.status = getattr(issue.fields, issue_fields['Status']).name
        self.time_spent = getattr(issue.fields, issue_fields['Time Spent'], 0) or 0
        self.time_estimate = getattr(issue.fields, issue_fields['Remaining Estimate'], 0) or 0
        self.is_epic = getattr(issue.fields, issue_fields['Issue Type']).name == 'Epic'
        try:
            self.account = getattr(issue.fields, issue_fields['Account']).name
        except AttributeError:  # Inherited account in a subtask is null
            self.account = None

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

        self.is_relevant = self._is_relevant_for_current_cell(cell_key, cell_members)
        self.is_flagged = self._is_flagged(issue, issue_fields)

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
        try:
            return self.get_bot_directive(settings.SPRINT_REVIEW_DIRECTIVE)

        except ValueError:
            # If we want to plan review time for epic or ticket with `SPRINT_STATUS_NO_MORE_REVIEW` status,
            # we need to specify it with bot's directive.
            if self.is_epic or self.status in settings.SPRINT_STATUS_NO_MORE_REVIEW:
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

    def _is_relevant_for_current_cell(self, cell_key: str, cell_members: List[str]) -> bool:
        """
        Helper method for determining whether the issue is "relevant" for the current cell.
        The issue is "relevant" when it matches one of the following conditions:
        - Belongs to the project related to the cell (i.e. has the cell-specific prefix). When this condition is met,
          Jira restricts the assignees to the members of the cell. Therefore we don't need to check assignees.
        - Has the reviewer 1 from the current cell.

        Note: currently we don't consider reviewer 2 role in Sprints.
        """
        return self.key.startswith(cell_key) or self.reviewer_1.name in cell_members

    @staticmethod
    def _is_flagged(issue: Issue, issue_fields: Dict[str, str]) -> bool:
        """Check whether the ticket has been flagged as "Impediment"."""
        return any(filter(lambda x: x.value == 'Impediment', getattr(issue.fields, issue_fields['Flagged']) or []))


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
        self.flagged_time = 0
        self.current_unestimated: List[DashboardIssue] = []
        self.future_unestimated: List[DashboardIssue] = []
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
            self.current_unestimated.append(issue)
        else:
            self.future_unestimated.append(issue)


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
        self.cell_key: str
        self.active_sprints: List[Sprint]
        self.cell_future_sprint: Sprint
        self.future_sprints: List[Sprint]
        self.future_sprint_start: str
        self.future_sprint_end: str

        # Retrieve data from Jira.
        self.cell_key = get_cell_key(conn, board_id)
        self.get_sprints()
        self.create_mock_users()
        self.vacations = get_vacations(self.before_future_sprint_start, self.after_future_sprint_end)
        self.get_issues()
        self.generate_rows()

    @property
    def rows(self):
        """Simplification for the serializer."""
        return self.dashboard.values()

    def get_sprints(self) -> None:
        """Retrieves current and future sprint for the board."""
        sprints = get_all_sprints(self.jira_connection, self.board_id)
        self.active_sprints = sprints['active']
        self.future_sprints = sprints['future']
        self.cell_future_sprint = get_next_sprint(sprints['cell'], sprints['cell'][0])

        self.future_sprint_start = get_sprint_start_date(self.cell_future_sprint)
        self.future_sprint_end = get_sprint_end_date(self.cell_future_sprint)

        # Helper variables to retrieve more data for different timezones (one extra day on each end of the sprint).
        self.before_future_sprint_start = (parse(self.future_sprint_start) - timedelta(days=1)).strftime(
            settings.JIRA_API_DATE_FORMAT
        )
        self.after_future_sprint_end = (parse(self.future_sprint_end) + timedelta(days=1)).strftime(
            settings.JIRA_API_DATE_FORMAT
        )

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
        self.sprint_division = get_sprint_meeting_day_division(self.future_sprint_start)
        self.issues = []

        active_sprint_ids = {sprint.id for sprint in self.active_sprints}
        for issue in issues:
            dashboard_issue = DashboardIssue(
                issue,
                active_sprint_ids,
                self.members,
                self.unassigned_user,
                self.other_cell,
                self.issue_fields,
                self.cell_key,
            )
            if dashboard_issue.is_relevant:
                self.issues.append(dashboard_issue)

        for member in self.members:
            schedule = self.jira_connection.user_schedule(
                member,
                self.before_future_sprint_start,
                self.after_future_sprint_end,
            )
            self.commitments[member] = {
                'total': schedule.requiredSeconds,
                'days': {day.date: day.requiredSeconds for day in schedule.days}
            }

    @typing.no_type_check
    def generate_rows(self) -> None:
        """Generates rows for all users and calculates their time stats."""
        for issue in self.issues:  # type: DashboardIssue
            assignee = self.dashboard.setdefault(issue.assignee, DashboardRow(issue.assignee))
            reviewer_1 = self.dashboard.setdefault(issue.reviewer_1, DashboardRow(issue.reviewer_1))

            # Calculate time for epic management
            if issue.is_epic:
                assignee.future_epic_management_time += issue.epic_management_time
                continue

            # Calculate hours for recurring tickets for the upcoming sprint.
            if issue.status == settings.SPRINT_STATUS_RECURRING:
                assignee.future_assignee_time += issue.recurring_time
                reviewer_1.future_review_time += issue.review_time
                continue

            # Check if the issue has any time left.
            if issue.time_estimate == 0:
                assignee.add_unestimated_issue(issue)

            # Calculations for the current sprint.
            if issue.current_sprint:
                # Assume that no more review will be needed at this point.
                if issue.status == settings.SPRINT_STATUS_EXTERNAL_REVIEW:
                    assignee.current_remaining_upstream_time += issue.assignee_time

                else:
                    reviewer_1.current_remaining_review_time += issue.review_time
                    assignee.current_remaining_assignee_time += issue.assignee_time

            # Calculations for the upcoming sprint.
            else:
                assignee.future_assignee_time += issue.assignee_time
                reviewer_1.future_review_time += issue.review_time

                if issue.is_flagged:
                    assignee.flagged_time += issue.assignee_time
                    reviewer_1.flagged_time += issue.review_time

        self.dashboard.pop(self.other_cell, None)

        # Hide users that are not included in the Sprint board's quickfilters.
        for user in list(self.dashboard.keys()):
            if user != self.unassigned_user and user.name not in self.members:
                self.dashboard.pop(user)

        self._calculate_commitments()

    @typing.no_type_check
    def _calculate_commitments(self):
        """
        Calculates time commitments and vacations for each user.
        """
        for row in self.rows:
            if row.user != self.unassigned_user:
                # Calculate vacations
                for vacation in self.vacations:
                    if row.user.displayName.startswith(vacation["user"]):
                        for vacation_date in daterange(
                            max(
                                vacation["start"]["date"],
                                (parse(self.future_sprint_start) - timedelta(days=1)).strftime(
                                    settings.JIRA_API_DATE_FORMAT
                                ),
                            ),
                            min(
                                vacation["end"]["date"],
                                (parse(self.future_sprint_end) + timedelta(days=1)).strftime(
                                    settings.JIRA_API_DATE_FORMAT
                                ),
                            ),
                        ):
                            row.vacation_time += self._get_vacation_for_day(
                                self.commitments[row.user.name]["days"][vacation_date],
                                vacation_date,
                                vacation["seconds"],
                                row.user.displayName,
                            )
                    elif row.user.displayName < vacation["user"]:
                        # Small optimization, as users' vacations are sorted.
                        break

                # Remove the "padding" from a day before and after the sprint.
                # noinspection PyTypeChecker
                row.set_goal_time(
                    self.commitments[row.user.name]["total"]
                    - self.commitments[row.user.name]["days"][self.before_future_sprint_start]
                    - self.commitments[row.user.name]["days"][self.after_future_sprint_end]
                    - row.vacation_time
                )

    def _get_vacation_for_day(self, commitments: int, date: str, planned_commitments: int, username: str) -> float:
        """
        Returns vacation time for specific users during a day.

        Because of the timezones we need to consider 4 edge cases. When vacations are scheduled:
        1. For the last day of the active sprint, there are two subcases:
            a. Positive timezone - this day is completely a part of the active sprint, so this time is ignored (0).
            b. Negative timezone - this day can span the active and next sprint, because user can work after the sprint
               ends. The ratio is represented by `1 - division`.
        2. For the first day of the next sprint, there are two subcases:
            a. Positive timezone - this day can span the active and next sprint, because user can work after the sprint
               ends. The ratio is represented by `1 - division`.
            b. Negative timezone - this day is completely a part of the next sprint, so it is counted as vacations.
        3. For the last day of the next sprint, there are two subcases:
            a. Positive timezone - this day is completely a part of the next sprint, so it is counted as vacations.
            b. Negative timezone - this day can span the next and future next sprint, because user can work after
               the sprint ends. The ratio is represented by `division`.
        4. For the first day of the future next sprint, there are two subcases:
            a. Positive timezone - this day can span the next and future next sprint, because user can work after
               the sprint ends. The ratio is represented by `division`.
            b. Negative timezone - this day is completely a part of the future next sprint, so this time is ignored (0).

        `division` - a part of the user's availability before the start of the sprint.

        TODO: Check whether this works correctly with other sprint start times than midnight UTC.
              For these it can span 3 days, so we might have 6 (or even more) corner cases.
        """
        division, positive_timezone = self.sprint_division[username]
        vacations = commitments - planned_commitments

        if date < self.future_sprint_start:
            return vacations * (1 - division) if not positive_timezone else 0
        elif date == self.future_sprint_start:
            return vacations * (1 - division) if positive_timezone else vacations
        elif date == self.future_sprint_end:
            return vacations * division if not positive_timezone else vacations
        elif date > self.future_sprint_end:
            return vacations * division if positive_timezone else 0

        return vacations
