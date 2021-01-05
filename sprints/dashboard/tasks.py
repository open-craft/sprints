import string
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Dict,
    List,
)

from celery import group
# noinspection PyProtectedMember
from celery.result import allow_join_result
from django.conf import settings
# noinspection PyProtectedMember
from django.core.cache import cache
from jira.resources import (
    Issue,
    Sprint,
)

from config import celery_app
from sprints.dashboard.libs.google import (
    get_commitments_spreadsheet,
    get_rotations_users,
    upload_commitments,
    upload_spillovers,
)
from sprints.dashboard.libs.jira import connect_to_jira
from sprints.dashboard.models import Dashboard
from sprints.webhooks.models import Webhook, WebhookEvent
from sprints.dashboard.utils import (
    create_next_sprint,
    filter_sprints_by_cell,
    get_all_sprints,
    get_cell_member_names,
    get_cell_member_roles,
    get_cell_members,
    get_cells,
    get_commitment_range,
    get_issue_fields,
    get_meetings_issue,
    get_next_sprint,
    get_spillover_issues,
    get_sprint_number,
    get_sprints,
    prepare_clean_sprint_rows,
    prepare_commitment_spreadsheet,
    prepare_jql_query_active_sprint_tickets,
    prepare_jql_query_cell_role_epic,
    prepare_spillover_rows,
)


@celery_app.task(ignore_result=True)
def upload_spillovers_task(board_id: int, cell_name: str) -> None:
    """A task for documenting spillovers in the Google Spreadsheet."""
    with connect_to_jira() as conn:
        issue_fields = get_issue_fields(conn, settings.SPILLOVER_REQUIRED_FIELDS)
        issues = get_spillover_issues(conn, issue_fields, cell_name)
        active_sprints = get_all_sprints(conn)['active']
        meetings = get_meetings_issue(conn, cell_name, issue_fields)
        members = get_cell_member_names(conn, get_cell_members(conn.quickfilters(board_id)))

    active_sprints_dict = {int(sprint.id): sprint for sprint in active_sprints}
    rows = prepare_spillover_rows(issues, issue_fields, active_sprints_dict)
    prepare_clean_sprint_rows(rows, members, meetings, issue_fields, active_sprints_dict)
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
def add_spillover_reminder_comment_task(issue_key: str, assignee_key: str, clean_sprint: bool = False) -> None:
    """A task for posting the spillover reason reminder on the issue."""
    message = settings.SPILLOVER_CLEAN_HINTS_MESSAGE if clean_sprint else settings.SPILLOVER_REMINDER_MESSAGE
    with connect_to_jira() as conn:
        conn.add_comment(
            issue_key,
            f"[~{assignee_key}], {message}"
        )


@celery_app.task(ignore_result=True)
def create_next_sprint_task(board_id: int) -> int:
    """A task for creating the next sprint for the specified cell."""
    with connect_to_jira() as conn:
        cells = get_cells(conn)
        cell = next(c for c in cells if c.board_id == board_id)
        sprints: List[Sprint] = get_sprints(conn, cell.board_id)

        next_sprint = create_next_sprint(conn, sprints, cell.key, board_id)
    return get_sprint_number(next_sprint)


@celery_app.task(ignore_result=True)
def create_role_issues_task(cell: Dict[str, str], sprint_id: int, sprint_number: int) -> None:
    """A task for posting the spillover reason reminder on the issue."""
    rotations = get_rotations_users(str(sprint_number), cell['name'])
    with connect_to_jira() as conn:
        jira_fields = get_issue_fields(conn, settings.JIRA_REQUIRED_FIELDS)
        epic = conn.search_issues(
            **prepare_jql_query_cell_role_epic(
                ['None'],  # We don't need any fields here. The `key` attribute will be sufficient.
                project=cell['name'],
            ),
            maxResults=1,
        )[0]

        fields = {
            'project': cell['key'],
            jira_fields['Issue Type']: 'Story',
            jira_fields['Sprint']: sprint_id,
            jira_fields['Epic Link']: epic.key,
        }

        for role, users in rotations.items():
            for sprint_part, user in enumerate(users):
                user_name = conn.search_users(user)[0].name
                fields.update({
                    jira_fields['Assignee']: {'name': user_name},
                    jira_fields['Reviewer 1']: {'name': user_name},
                })
                for subrole in settings.JIRA_CELL_ROLES.get(role, []):
                    fields.update({
                        jira_fields['Summary']:
                            f"Sprint {sprint_number}{string.ascii_lowercase[sprint_part]} {subrole['name']}",
                        jira_fields['Story Points']: subrole['story_points'],
                        # This needs to be string.
                        jira_fields['Account']: str(subrole.get('account', settings.JIRA_CELL_ROLE_ACCOUNT)),
                        # This requires special dict structure.
                        'timetracking': {'originalEstimate': f"{subrole['hours']}h"},
                    })

                    conn.create_issue(fields)

@celery_app.task(ignore_result=True)
def trigger_new_sprint_webhooks(cell: Dict[str, str], sprint_name: str, sprint_number: int, board_id: int):
    """
    1. Gather a dictionary mapping Name to E-Mail Address of members
    2. Gather cell member roles
    3. Map E-Mails to Cell member roles
    4. Add rotations (DD, FF etc) to the Cell member roles array
    5. Trigger webhooks

    The webhook receivers identify users by E-Mail, but our spreadsheets & documentation identify them
    by name, so we must map the two. It is important that the spelling of member names is consistent in
    the documentation.
    """
    with connect_to_jira() as conn:
        participants_payload: Dict[str, List[str]] = {}

        # Create dictionary mapping names to E-Mails: {'John Doe': 'john@opencraft.com',...}
        cell_member_emails = {}
        for member in get_cell_members(conn.quickfilters(board_id)):
            user = conn.user(member)
            cell_member_emails[user.displayName] = user.emailAddress

        # Dictionary containing member roles: {'John Doe': ['Sprint Planning Manager', ...],...}
        cell_member_roles = get_cell_member_roles()

        # Dictionary containing rotations: {'FF': ['John Doe',...],...}
        rotations = get_rotations_users(str(sprint_number), cell['name'])
        
        for member_name, member_email in cell_member_emails.items():
            participants_payload[member_email] = []

            # Not all members have atleast one role assigned to them
            if member_name in cell_member_roles:
                participants_payload[member_email].extend(cell_member_roles[member_name])

            # If member has rotation, specify which rotation
            for duty, assignees in rotations.items():
                for idx, assignee in enumerate(assignees):
                    # The rotations sheet sometimes contains only the first name
                    if member_name.startswith(assignee):
                        participants_payload[member_email].append("%s-%d" % (duty, idx+1))

        payload = {
            'board_id': board_id,
            'cell': cell['name'],
            'sprint_number': sprint_number,
            'sprint_name': sprint_name,
            'participants': participants_payload,
            'event_name': "new sprint",
        }

        webhooks = Webhook.objects.filter(events__name="new sprint")
        for webhook in webhooks:
            webhook.trigger(payload=payload)

@celery_app.task(ignore_result=True)
def complete_sprint_task(board_id: int) -> None:
    """
    1. Uploads spillovers.
    2. Uploads commitments.
    3. Trigger start of new sprint webhooks #TODO: Update order
    4. Moves archived issues out of the active sprint.
    5. Closes the active sprint.
    6. Moves issues from the closed sprint to the next one.
    7. Opens the next sprint.
    8. Creates role tickets.
    9. Releases the sprint completion lock.
    10. Clears cache related to end of sprint date.
    """
    with connect_to_jira() as conn:
        cells = get_cells(conn)
        cell = next(c for c in cells if c.board_id == board_id)
        spreadsheet_tasks = [
            upload_spillovers_task.s(cell.board_id, cell.name),
            upload_commitments_task.s(cell.board_id, cell.name),
        ]

        # Run the spreadsheet tasks asynchronously and wait for the results before proceeding with ending the sprint.
        with allow_join_result():
            # FIXME: Use `apply_async`. Currently blocked because of `https://github.com/celery/celery/issues/4925`.
            #   CAUTION: if you change it, ensure that all tasks have finished successfully.
            #group(spreadsheet_tasks).apply().join()
            pass #TODO: REMOVE

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

        cell_dict = {
            'key': cell.key,
            'name': cell.name,
            'board_id': cell.board_id,
        }

        # It is not mentioned in Python lib docs, but the limit for the issue-moving queries is 50 issues. Source:
        # https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-backlog-issue-post
        # https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-sprint-sprintId-issue-post
        batch_size = 50
        trigger_new_sprint_webhooks.delay(cell_dict, next_sprint.name, get_sprint_number(next_sprint), board_id) #TODO: REMOVE
        if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
            if settings.FEATURE_CELL_ROLES:
                # Raise error if we can't read roles from the handbook
                get_cell_member_roles(raise_exception=True)

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
            # Get next sprint number for creating role tasks there.
            if future_next_sprint := get_next_sprint(sprints, next_sprint):
                future_next_sprint_number = get_sprint_number(future_next_sprint)
            else:
                future_next_sprint_number = create_next_sprint_task(board_id)
                future_next_sprint = get_next_sprint(sprints, next_sprint)

            create_role_issues_task.delay(cell_dict, future_next_sprint.id, future_next_sprint_number)

            trigger_new_sprint_webhooks.delay(cell_dict, next_sprint.name, get_sprint_number(next_sprint), board_id)

    cache.delete(f'{settings.CACHE_SPRINT_END_LOCK}{board_id}')  # Release a lock.
    cache.delete(f"{settings.CACHE_SPRINT_END_DATE_PREFIX}active")
    cache.delete(f"{settings.CACHE_SPRINT_END_DATE_PREFIX}cell{board_id}")
    cache.delete(f"{settings.CACHE_SPRINT_END_DATE_PREFIX}future")
