import string
from datetime import datetime, timedelta
from typing import Dict, List

from celery import group
# noinspection PyProtectedMember
from celery.result import allow_join_result
from dateutil.parser import parse
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import make_aware
from django_celery_beat.models import (
    IntervalSchedule,
    PeriodicTask,
)
# noinspection PyProtectedMember
from jira.resources import Issue, Sprint

from config import celery_app
from sprints.dashboard.automation import (
    check_issue_injected,
    get_next_sprint_issues,
    get_overcommitted_users,
    get_specific_day_of_sprint,
    group_incomplete_issues,
    notify_about_injection,
    unflag_issue,
)
from sprints.dashboard.libs.google import (
    get_commitments_spreadsheet,
    get_rotations_users,
    upload_commitments,
    upload_spillovers,
)
from sprints.dashboard.libs.jira import connect_to_jira
from sprints.dashboard.libs.mattermost import create_mattermost_post
from sprints.dashboard.models import Dashboard
from sprints.dashboard.utils import (
    compile_participants_roles,
    create_next_sprint,
    filter_sprints_by_cell,
    get_all_sprints,
    get_cell_member_names,
    get_cell_member_roles,
    get_cell_members,
    get_cell_membership,
    get_cells,
    get_commitment_range,
    get_current_sprint_end_date,
    get_issue_fields,
    get_meetings_issue,
    get_next_sprint,
    get_spillover_issues,
    get_sprint_by_name,
    get_sprint_number,
    get_sprints,
    prepare_clean_sprint_rows,
    prepare_commitment_spreadsheet,
    prepare_jql_query_active_sprint_tickets,
    prepare_jql_query_cell_role_epic,
    prepare_spillover_rows,
)
from sprints.webhooks.models import Webhook


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
def trigger_new_sprint_webhooks_task(cell_name: str, sprint_name: str, sprint_number: int, board_id: int):
    """
    1. Collects a dictionary of rotations, and the cell members.
    2. Collects the usernames of the cell members of a board.
    3. Collects the cell members and their associated roles.
    4. Associates the cell members' info with their roles, and their rotations.
    5. Triggers the active 'new sprint' webhooks.
    """
    with connect_to_jira() as conn:
        # Dictionary containing rotations: {'FF': ['John Doe',...],...}
        rotations = get_rotations_users(str(sprint_number), cell_name)

        # A list of jira usernames for a board: ['johndoe1', 'jane_doe_22', ...]
        members = []
        usernames = get_cell_members(conn.quickfilters(board_id))
        for username in usernames:
            members.append(conn.user(username))

        # Dictionary containing member roles: {'John Doe': ['Sprint Planning Manager', ...],...}
        cell_member_roles = get_cell_member_roles()

        payload = {
            'board_id': board_id,
            'cell': cell_name,
            'sprint_number': sprint_number,
            'sprint_name': sprint_name,
            'participants': compile_participants_roles(members, rotations, cell_member_roles),
            'event_name': "new sprint",
        }

        webhooks = Webhook.objects.filter(events__name="new sprint", active=True)
        for webhook in webhooks:
            webhook.trigger(payload=payload)


@celery_app.task(ignore_result=True)
def complete_sprint_task(board_id: int) -> None:
    """
    1. Upload spillovers.
    2. Upload commitments.
    3. Move archived issues out of the active sprint.
    4. Close the active sprint.
    5. Move issues from the closed sprint to the next one.
    6. Open the next sprint.
    7. Create role tickets.
    8. Trigger the `new sprint` webhooks.
    9. Release the sprint completion lock and clear the cache related to end of sprint date.
    10. Schedule asynchronous sprint planning tasks for the new sprint, if SPRINT_ASYNC_AUTOMATION_ENABLED is set.
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
        if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
            if settings.FEATURE_CELL_ROLES:
                # Raise error if we can't read roles from the handbook
                get_cell_member_roles()

            # Remove archived tickets from the active sprint. Leaving them might interrupt closing the sprint.
            conn.move_to_backlog(archived_issue_keys)

            # Close the active sprint.
            conn.update_sprint(
                active_sprint.id,
                name=active_sprint.name,
                startDate=active_sprint.startDate,
                endDate=active_sprint.endDate,
                state='closed',
            )

            # Move issues to the next sprint from the closed one.
            conn.add_issues_to_sprint(next_sprint.id, issue_keys)

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

            cell_dict = {
                'key': cell.key,
                'name': cell.name,
                'board_id': cell.board_id,
            }

            create_role_issues_task.delay(cell_dict, future_next_sprint.id, future_next_sprint_number)

            trigger_new_sprint_webhooks_task.delay(
                cell.name, next_sprint.name, get_sprint_number(next_sprint), board_id
            )

    cache.delete_many(
        [
            f'{settings.CACHE_SPRINT_END_LOCK}{board_id}',  # Release the lock.
            f'{settings.CACHE_SPRINT_START_DATE_PREFIX}active',
            f'{settings.CACHE_SPRINT_START_DATE_PREFIX}cell{board_id}',
            f'{settings.CACHE_SPRINT_START_DATE_PREFIX}future',
        ]
    )

    if settings.SPRINT_ASYNC_AUTOMATION_ENABLED:
        schedule_sprint_tasks_task.delay()


@celery_app.task(ignore_result=True)
def schedule_sprint_tasks_task() -> None:
    """
    Create task schedules for the current sprint.

    There are currently two types of tasks. Both of them use the `IntervalSchedule` for simplification.
    1. One-off - scheduled to run every second to ensure they will be invoked on time. After the first run, the
       `Enabled` option is set to `False` in the database.
    2. Periodic (non-one-off) - ran hourly until the end of the sprint +1 minute, so they are invoked on the hour of the
       sprint end as well.
    """
    get_specific_day_of_sprint(settings.SPRINT_ASYNC_TICKET_CREATION_CUTOFF_DAY)
    # One extra minute to ensure that the task will be scheduled on time. Otherwise it might get revoked.
    expiration_date = parse(get_current_sprint_end_date()) + timedelta(days=1, minutes=1)

    for task_path, task_details in settings.SPRINT_ASYNC_TASKS.items():
        # If there are more than one tasks with the same path, then remove all of them.
        query = PeriodicTask.objects.filter(task=task_path)
        if query.count() > 1:
            query.delete()

        start_time = get_specific_day_of_sprint(task_details['start'])
        one_off = task_details['one_off']
        interval, _ = IntervalSchedule.objects.get_or_create(
            every=1, period=IntervalSchedule.SECONDS if one_off else IntervalSchedule.HOURS
        )

        task_data = dict(
            name=task_details['name'],
            enabled=True,
            start_time=make_aware(start_time),
            expires=make_aware(expiration_date),
            interval=interval,
            one_off=one_off,
        )

        PeriodicTask.objects.update_or_create(task=task_path, defaults=task_data)


@celery_app.task(ignore_result=True)
def move_out_injections_task() -> None:
    """
    Move injected tickets out of the next sprint to the `SPRINT_ASYNC_INJECTION_SPRINT`.
    Then notify assignees and epic owners about this, if they exist.
    """
    with connect_to_jira() as conn:
        injection_sprint = get_sprint_by_name(conn, settings.SPRINT_ASYNC_INJECTION_SPRINT)
        issues = get_next_sprint_issues(conn, changelog=True)

        injections = [issue for issue in issues if check_issue_injected(conn, issue)]
        injections_keys = [issue.key for issue in injections]
        if not settings.DEBUG:  # We should not trigger this in the dev environment.
            conn.add_issues_to_sprint(injection_sprint.id, injections_keys)
        for injection in injections:
            notify_about_injection(conn, injection, injection_sprint)


@celery_app.task(ignore_result=True)
def check_tickets_ready_for_sprint_task() -> None:
    """Notify team members about incomplete tickets."""
    with connect_to_jira() as conn:
        cell_membership = get_cell_membership(conn)
        issues = get_next_sprint_issues(conn)

        for user, incomplete_issues in group_incomplete_issues(conn, issues).items():
            # TODO: Add more flexibility to the Mattermost library, to support a nicer format here.
            message = settings.SPRINT_ASYNC_INCOMPLETE_TICKET_MESSAGE + str(incomplete_issues)
            emails = [user.emailAddress]
            # If user is not a member of any cell, then use a default Mattermost channel.
            cell = cell_membership.get(user.name, settings.MATTERMOST_CHANNEL)

            if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
                create_mattermost_post(message, emails=emails, channel=cell)


@celery_app.task(ignore_result=True)
def ping_overcommitted_users_task() -> None:
    """Notify team members about their overcommitment."""
    with connect_to_jira() as conn:
        for cell, users in get_overcommitted_users(conn).items():
            # TODO: Ping sprint managers too. Use the approach from https://github.com/open-craft/sprints/pull/63.
            #  Add more flexibility to the Mattermost library to handle this.
            emails = [user.emailAddress for user in users]
            message = settings.SPRINT_ASYNC_OVERCOMMITMENT_MESSAGE

            if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
                create_mattermost_post(message, emails=emails, channel=cell)


@celery_app.task(ignore_result=True)
def unflag_tickets_task() -> None:
    """Unflag all tickets from the next sprint."""
    with connect_to_jira() as conn:
        issues = get_next_sprint_issues(conn)
        for issue in issues:
            if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
                unflag_issue(conn, issue)
