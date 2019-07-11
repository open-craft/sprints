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
    2. Completes the sprints for each cell and opens new ones.
    3. Moves issues from previous sprints to the next ones.
    """
    upload_spillovers_task()
    cells = get_cells()
    with connect_to_jira() as conn:
        for cell in cells:
            sprints: List[Sprint] = conn.sprints(cell.board_id, state='active, future')
            active_sprint = None
            for sprint in sprints:
                if sprint.name.startswith('Sprint') and sprint.state == 'active':
                    active_sprint = sprint
                    break
            if active_sprint:
                future_sprint = find_next_sprint(sprints, active_sprint)
            else:
                for sprint in sprints:
                    if sprint.name.startswith('Sprint'):
                        future_sprint = sprint
                        break

            issues: List[Issue] = conn.search_issues(
                **prepare_jql_query_active_sprint_tickets(
                    list(),  # We don't need any fields here. The `key` will be sufficient.
                    settings.SPRINT_STATUS_SPILLOVER | {settings.SPRINT_STATUS_EXTERNAL_REVIEW,
                                                        settings.SPRINT_STATUS_RECURRING},
                    project=cell.name,
                ),
                maxResults=0,
            )
            issue_keys = [issue.key for issue in issues]

            # Close active sprint and open future one.
            conn.update_sprint(active_sprint.id, state='closed')
            conn.update_sprint(future_sprint.id, state='active')

            # Move issues to the active sprint from the closed one.
            # It is not mentioned in Python lib docs, but the limit for the next query is 50 issues. Source:
            # https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-sprint-sprintId-issue-post
            batch_size = 50
            for i in range(0, len(issue_keys), batch_size):
                batch = issue_keys[i:i + batch_size]
                conn.add_issues_to_sprint(future_sprint.id, batch)
