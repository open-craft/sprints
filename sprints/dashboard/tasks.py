from datetime import (
    datetime,
    timedelta,
)
from typing import List

from celery import group
# noinspection PyProtectedMember
from celery.result import allow_join_result
from django.conf import settings
# noinspection PyProtectedMember
from jira.resources import (
    Issue,
    Sprint,
)

from config import celery_app
from sprints.dashboard.libs.google import (
    get_commitments_spreadsheet,
    upload_commitments,
    upload_spillovers,
)
from sprints.dashboard.libs.jira import connect_to_jira
from sprints.dashboard.models import Dashboard
from sprints.dashboard.utils import (
    get_cells,
    get_commitment_range,
    get_issue_fields,
    get_next_sprint,
    get_spillover_issues,
    get_sprint_number,
    get_sprints,
    prepare_commitment_spreadsheet,
    prepare_jql_query_active_sprint_tickets,
    prepare_spillover_rows,
    get_all_sprints,
    filter_sprints_by_cell,
)


@celery_app.task(ignore_result=True)
def upload_spillovers_task(cell_name: str) -> None:
    """A task for documenting spillovers in the Google Spreadsheet."""
    with connect_to_jira() as conn:
        issue_fields = get_issue_fields(conn, settings.SPILLOVER_REQUIRED_FIELDS)
        issues = get_spillover_issues(conn, issue_fields, cell_name)
        active_sprints = get_all_sprints(conn)['active']

    active_sprints_dict = {int(sprint.id): sprint for sprint in active_sprints}
    rows = prepare_spillover_rows(issues, issue_fields, active_sprints_dict)
    upload_spillovers(rows)


@celery_app.task(ignore_result=True)
def upload_commitments_task(board_id: int, cell_name: str) -> None:
    """A task for uploading commitments in the Google Spreadsheet."""
    with connect_to_jira() as conn:
        dashboard = Dashboard(board_id, conn)

    dashboard.delete_mock_users()
    spreadsheet = get_commitments_spreadsheet(cell_name)
    users, column = prepare_commitment_spreadsheet(dashboard, spreadsheet)
    range_ = get_commitment_range(spreadsheet, cell_name)

    upload_commitments(users, column, range_)


@celery_app.task(ignore_result=True)
def add_spillover_reminder_comment_task(issue_key: str, assignee_key: str) -> None:
    """A task for posting the spillover reason reminder on the issue."""
    with connect_to_jira() as conn:
        conn.add_comment(
            issue_key,
            f"[~{assignee_key}], {settings.SPILLOVER_REMINDER_MESSAGE}"
        )


@celery_app.task(ignore_result=True)
def complete_sprint(board_id: int) -> None:
    """
    1. Uploads spillovers.
    2. Moves archived issues out of the active sprint.
    3. Closes the shared sprint.
    4. Moves issues from the closed sprint to the next one.
    5. Opens the next shared sprint.
    """
    with connect_to_jira() as conn:
        cells = get_cells(conn)
        cell = next(c for c in cells if c.board_id == board_id)
        spreadsheet_tasks = [upload_spillovers_task.s(cell.name), upload_commitments_task.s(cell.board_id, cell.name)]

        # Run the spreadsheet tasks asynchronously and wait for the results before proceeding with ending the sprint.
        with allow_join_result():
            # FIXME: Use `apply_async`. Currently blocked because of `https://github.com/celery/celery/issues/4925`.
            group(spreadsheet_tasks).apply().join()

        sprints: List[Sprint] = get_sprints(conn, cell.board_id)
        sprints = filter_sprints_by_cell(sprints, cell.key)

        for sprint in sprints:
            if sprint.state == 'active':
                active_sprint = sprint
                break

        next_sprint = get_next_sprint(sprints, active_sprint)

        archived_issues: List[Issue] = conn.search_issues(
            **prepare_jql_query_active_sprint_tickets(
                ['None'],  # We don't need any fields here. The `key` attribute will be sufficient.
                {settings.SPRINT_STATUS_ARCHIVED},
                project=cell.name,
            ),
            maxResults=0,
        )
        archived_issue_keys = [issue.key for issue in archived_issues]

        issues: List[Issue] = conn.search_issues(
            **prepare_jql_query_active_sprint_tickets(
                ['None'],  # We don't need any fields here. The `key` attribute will be sufficient.
                settings.SPRINT_STATUS_ACTIVE | {settings.SPRINT_STATUS_DEPLOYED_AND_DELIVERED},
                project=cell.name,
            ),
            maxResults=0,
        )
        issue_keys = [issue.key for issue in issues]

        # It is not mentioned in Python lib docs, but the limit for the issue-moving queries is 50 issues. Source:
        # https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-backlog-issue-post
        # https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-sprint-sprintId-issue-post
        batch_size = 50
        if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
            # Remove archived tickets from the active sprint. Leaving them might interrupt closing the sprint.
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

            # Ensure that the next sprint exists. If it doesn't exist, create it.
            future_next_sprint = get_next_sprint(sprints, next_sprint)
            if not future_next_sprint:
                future_next_sprint_number = get_sprint_number(next_sprint) + 1
                future_name_date = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
                future_end_date = end_date + timedelta(days=settings.SPRINT_DURATION_DAYS)
                conn.create_sprint(
                    name=f'{cell.key}.{future_next_sprint_number} ({future_name_date})',
                    board_id=cell.board_id,
                    startDate=end_date.isoformat(),
                    endDate=future_end_date.isoformat(),
                )
