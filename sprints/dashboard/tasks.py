from datetime import (
    datetime,
    timedelta,
)
from typing import List

from django.conf import settings
# noinspection PyProtectedMember
from jira.resources import (
    Issue,
    Sprint,
)

from config import celery_app
from config.settings.base import SPILLOVER_REQUIRED_FIELDS
from sprints.dashboard.libs.google import upload_spillovers
from sprints.dashboard.libs.jira import connect_to_jira
from sprints.dashboard.utils import (
    find_next_sprint,
    get_cells,
    get_issue_fields,
    get_spillover_issues,
    get_sprints,
    prepare_jql_query_active_sprint_tickets,
    prepare_spillover_rows,
)


@celery_app.task(ignore_result=True)
def upload_spillovers_task():
    """A task for documenting spillovers in the Google Spreadsheet."""
    with connect_to_jira() as conn:
        issue_fields = get_issue_fields(conn, SPILLOVER_REQUIRED_FIELDS)
        issues = get_spillover_issues(conn, issue_fields)

    rows = prepare_spillover_rows(issues, issue_fields)
    upload_spillovers(rows)


@celery_app.task(ignore_result=True)
def complete_sprints():
    """
    1. Uploads spillovers.
    2. Moves archived issues out of the active sprint.
    3. Closes the shared sprint.
    4. Moves issues from the closed sprint to the next one.
    5. Opens the next shared sprint.
    """
    upload_spillovers_task()
    with connect_to_jira() as conn:
        cell = get_cells(conn)[0]  # The sprint is shared between cells, so we need only one ID.
        sprints: List[Sprint] = get_sprints(conn, cell.board_id)
        for sprint in sprints:
            if sprint.state == 'active':
                active_sprint = sprint
                break

        next_sprint = find_next_sprint(sprints, active_sprint, conn)

        archived_issues: List[Issue] = conn.search_issues(
            **prepare_jql_query_active_sprint_tickets(
                list(),  # We don't need any fields here. The `key` attribute will be sufficient.
                {settings.SPRINT_STATUS_ARCHIVED},
            ),
            maxResults=0,
        )
        archived_issue_keys = [issue.key for issue in archived_issues]

        issues: List[Issue] = conn.search_issues(
            **prepare_jql_query_active_sprint_tickets(
                list(),  # We don't need any fields here. The `key` attribute will be sufficient.
                settings.SPRINT_STATUS_ACTIVE | {settings.SPRINT_STATUS_DEPLOYED_AND_DELIVERED},
            ),
            maxResults=0,
        )
        issue_keys = [issue.key for issue in issues]

        # It is not mentioned in Python lib docs, but the limit for the issue-moving queries is 50 issues. Source:
        # https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-backlog-issue-post
        # https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-sprint-sprintId-issue-post
        batch_size = 50
        if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
            # Remove archived tickets from the active sprint. Leaving them might interrupt closing the sprint properly.
            for i in range(0, len(archived_issue_keys), batch_size):
                batch = archived_issue_keys[i:i + batch_size]
                conn.move_to_backlog(batch)

            # Close the active sprint.
            conn.update_sprint(
                active_sprint.id,
                name=active_sprint.name,
                startDate=active_sprint.startDate,
                endDate=active_sprint.endDate,
                state='closed',
            )

            # Move issues to the next sprint from the closed one.
            for i in range(0, len(issue_keys), batch_size):
                batch = issue_keys[i:i + batch_size]
                conn.add_issues_to_sprint(next_sprint.id, batch)

            # Open the next sprint.
            start_date = datetime.now()
            end_date = datetime.now() + timedelta(days=settings.SPRINT_DURATION_DAYS)
            conn.update_sprint(
                next_sprint.id,
                name=next_sprint.name,
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                state='active',
            )
