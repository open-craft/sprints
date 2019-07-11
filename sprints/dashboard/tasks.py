from config import celery_app
from config.settings.base import SPILLOVER_REQUIRED_FIELDS
from sprints.dashboard.libs.google import upload_spillovers
from sprints.dashboard.libs.jira import connect_to_jira
from sprints.dashboard.utils import (
    get_issue_fields,
    get_spillover_issues,
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
