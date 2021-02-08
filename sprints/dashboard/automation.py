"""This module contains functions used for planning automated tasks performed in specific days."""
from collections import defaultdict
from datetime import (
    datetime,
    timedelta,
)
from multiprocessing.pool import ThreadPool

from dateutil.parser import parse
from django.conf import settings
from jira import Issue
from jira.resources import (
    Sprint,
    User,
)

from sprints.dashboard.libs.jira import CustomJira
from sprints.dashboard.models import Dashboard
from sprints.dashboard.utils import (
    get_all_sprints,
    get_cells,
    get_current_sprint_start_date,
    get_issue_fields,
)


def get_current_sprint_day() -> int:
    """
    Return the current day of the sprint.

    :return: Number indicating which day of the sprint is today.
    """
    start_date = get_current_sprint_start_date()
    return (datetime.now() - parse(start_date)).days + 1


def get_specific_day_of_sprint(day: int) -> datetime:
    """
    Return the specific day of the sprint.

    :param day: Number of the desired day of the sprint.
    :return: Date of the desired day of the sprint.
    """
    start_date = get_current_sprint_start_date()
    return parse(start_date) + timedelta(days=day - 1)


def get_next_sprint_issues(conn: CustomJira, changelog: bool = False) -> list[Issue]:
    """
    Retrieve all tickets scheduled for the next sprint.

    Filtering by sprints excludes non-cell tickets.

    :param conn: Jira connection.
    :param changelog: Include ticket's history.
    """
    sprints = get_all_sprints(conn)
    sprints_str = ",".join((str(s.id) for s in sprints['future']))
    return conn.search_issues(
        jql_str=f"Sprint IN ({sprints_str})",
        fields=list(get_issue_fields(conn, settings.JIRA_REQUIRED_FIELDS + settings.JIRA_AUTOMATION_FIELDS).values()),
        expand="changelog" if changelog else "",  # Retrieve history of changes for each issue.
        maxResults=0,
    )


def get_users_to_ping(conn: CustomJira, issue: Issue, epic_owner: bool = False) -> set[User]:
    """
    Return users, who should be pinged about the ticket.

    The assignee is included if the ticket is assigned.
    The epic owner is included if the ticket is unassigned or if the `epic_owner` option is set.
    The reporter is included if the ticket both:
        - is unassigned,
        - does not belong to an epic or the epic is unassigned.
    If none of the above is present, the error is reported to Sentry.

    :param conn: Jira connection.
    :param issue: Jira ticket.
    :param epic_owner: Should always include epic owner?
    :return: Unique names of users, who should be notified about the ticket.
    """
    users = set()
    # Ping assignee.
    if user := getattr(issue.fields, conn.issue_fields[settings.JIRA_FIELDS_ASSIGNEE]):
        users.add(user)

    # Ping epic owner.
    if (epic_key := getattr(issue.fields, conn.issue_fields[settings.JIRA_FIELDS_EPIC_LINK])) and (
        epic_owner or not users
    ):
        epic = conn.issue(epic_key)
        if user := getattr(epic.fields, conn.issue_fields[settings.JIRA_FIELDS_ASSIGNEE]):
            users.add(user)

    # Ping reporter.
    if (user := getattr(issue.fields, conn.issue_fields[settings.JIRA_FIELDS_REPORTER])) and not users:
        users.add(user)

    if not users and not settings.DEBUG:
        from sentry_sdk import capture_message

        capture_message(f"There is nobody to ping for ticket {issue.key}.")

    return users


def notify_about_injection(conn: CustomJira, issue: Issue, sprint: Sprint) -> None:
    """
    Add comments to the issue that has been injected and moved out of the next sprint.

    :param conn: Jira connection.
    :param issue: Injected issue.
    :param sprint: Sprint, to which the issue have been moved.
    """
    users = get_users_to_ping(conn, issue, epic_owner=True)
    message = ""

    for user in users:
        message += f"[~{user.name}], "

    message += f"{settings.SPRINT_ASYNC_INJECTION_MESSAGE}{sprint.name}."

    if not settings.DEBUG:  # We should not trigger this in the dev environment.
        conn.add_comment(issue.key, message)


def group_incomplete_issues(conn: CustomJira, issues: list[Issue]) -> defaultdict[User, dict[str, list[str]]]:
    """
    Compose a dict mapping users with dicts mapping users' tickets with lists of missing tickets' fields.

    Example structure:
    {
        user: {
            ticket: [
                "Assignee",
                "Story Points"
            ]
        }
    }

    :param conn: Jira connection.
    :param issues: List of Jira issues.
    :return: A dict, where users are bound to their tickets, which are bound to lists of missing fields.
    """
    result: defaultdict[User, dict[str, list[str]]] = defaultdict(dict)
    for issue in issues:
        if missing_fields := check_issue_missing_fields(conn, issue):
            for user in get_users_to_ping(conn, issue):
                result[user][issue.key] = missing_fields

    return result


def flag_issue(conn: CustomJira, issue: Issue) -> None:
    """
    Add the "Impediment" flag to an issue.

    :param conn: Jira connection.
    :param issue: Jira issue.
    """
    if not getattr(issue.fields, conn.issue_fields[settings.JIRA_FIELDS_FLAGGED]):
        issue.update(fields={conn.issue_fields[settings.JIRA_FIELDS_FLAGGED]: [{"value": "Impediment"}]})


def unflag_issue(conn: CustomJira, issue: Issue) -> None:
    """
    Remove the "Impediment" flag from an issue.

    :param conn: Jira connection.
    :param issue: Jira issue.
    """
    if getattr(issue.fields, conn.issue_fields[settings.JIRA_FIELDS_FLAGGED]):
        issue.update(fields={conn.issue_fields[settings.JIRA_FIELDS_FLAGGED]: None})


def check_issue_injected(conn: CustomJira, issue: Issue) -> bool:
    """
    Check if the issue has been injected into the sprint, i.e. it has been created after the cutoff date.

    The injection is determined by checking the last update of the "Sprint" value in the ticket.
    Therefore, if the ticket has been moved out of the sprint for a moment after the cutoff date, and then added back,
    it is still considered as an injection.

    The cutoff date is configured via the `SPRINT_ASYNC_TICKET_CREATION_CUTOFF_DAY` env variable.
    The injection can be "accepted" (ignored) by adding a `SPRINT_ASYNC_INJECTION_LABEL` to the ticket.

    Note: the link below and API docs indicate that the `changelog` contains all existing changes - the pagination has
    `maxResults = total` by default. This was tested with a ticket that has over 3500 items in the changelog and it
    worked as described. Most of these tickets should be fairly new, so they will not have such extensive
    changelogs, but it is worth to keep this in mind, as not all behaviors of the API are documented properly.
    https://community.atlassian.com/t5/Answers-Developer-Questions/How-to-get-complete-changelog-for-a-issue/qaq-p/501636]

    :param conn: Jira connection.
    :param issue: Jira issue.
    :return: Is the ticket an injection?
    """
    # The injection can to be "accepted" with a label.
    if settings.SPRINT_ASYNC_INJECTION_LABEL in getattr(issue.fields, conn.issue_fields[settings.JIRA_FIELDS_LABELS]):
        return False

    cutoff_date = get_specific_day_of_sprint(settings.SPRINT_ASYNC_TICKET_CREATION_CUTOFF_DAY).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )

    for history in reversed(issue.changelog.histories):
        # The updates are ordered from the newest to the oldest, so we can skip the ones done before the cutoff date.
        if history.created < cutoff_date:
            break

        if history.items[0].field == "Sprint":
            return True

    return False


def check_issue_missing_fields(conn: CustomJira, issue: Issue) -> list[str]:
    """
    Get a list of fields that are missing from a ticket to call it ready for a sprint.

    :param conn: Jira connection.
    :param issue: Jira issue.
    :return: List of missing fields.
    """
    missing_fields = []
    # TODO: Make this configurable. It might need some tweaks to handle default behaviors for various fields.
    for field in [settings.JIRA_FIELDS_ASSIGNEE, settings.JIRA_FIELDS_REVIEWER, settings.JIRA_FIELDS_STORY_POINTS]:
        if not getattr(issue.fields, conn.issue_fields[field]):
            missing_fields.append(field)

    return missing_fields


def get_overcommitted_users(conn: CustomJira) -> dict[str, list[User]]:
    """
    Retrieve users that have negative time left for the next sprint (i.e. are overcommitted).

    :param conn: Jira connection.
    :return: List of overcommitted users.
    """
    cells = get_cells(conn)
    result = dict[str, list[User]]()

    # Generate dashboards in parallel.
    with ThreadPool(processes=settings.MULTIPROCESSING_POOL_SIZE) as pool:
        results = [pool.apply_async(Dashboard, (cell.board_id, conn)) for cell in cells]
        dashboards = [result.get(settings.MULTIPROCESSING_TIMEOUT) for result in results]

    for dashboard in dashboards:
        overcommitted_users: list[User] = []
        for row in dashboard.rows:
            # Check if the user has `raw` value - this excludes artificial users, like "Unassigned".
            if row.remaining_time < 0 and row.user.raw:
                overcommitted_users.append(row.user)

        # Ignore cells without overcommitted users.
        if overcommitted_users:
            result[dashboard.cell.name] = overcommitted_users

    return result
