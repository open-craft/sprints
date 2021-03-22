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
from dateutil.parser import parse
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import make_aware
from django_celery_beat.models import (
    IntervalSchedule,
    PeriodicTask,
)
# noinspection PyProtectedMember
from jira.resources import (
    Issue,
    Sprint,
)

from config import celery_app
from sprints.dashboard.automation import (
    check_issue_injected,
    get_next_poker_session_name,
    get_next_sprint_issues,
    get_overcommitted_users,
    get_poker_session_final_vote,
    get_specific_day_of_sprint,
    get_unestimated_next_sprint_issues,
    group_incomplete_issues,
    ping_users_on_ticket,
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
        conn.add_comment(issue_key, f"[~{assignee_key}], {message}")


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

    if settings.FEATURE_SPRINT_AUTOMATION:
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
    default_expiration_date = parse(get_current_sprint_end_date()) + timedelta(days=1, minutes=1)

    for task_path, task_details in settings.SPRINT_ASYNC_TASKS.items():
        # If there are more than one tasks with the same path, then remove all of them.
        query = PeriodicTask.objects.filter(task=task_path)
        if query.count() > 1:
            query.delete()

        start_delay = task_details.get('start_delay', timedelta())
        start_time = get_specific_day_of_sprint(task_details['start']) + start_delay

        expiration_date = default_expiration_date
        if end := task_details.get('end'):
            end_delay = task_details.get('end_delay', timedelta())
            expiration_date = get_specific_day_of_sprint(end) + end_delay

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
            ping_users_on_ticket(
                conn,
                injection,
                f"{settings.SPRINT_ASYNC_INJECTION_MESSAGE}{injection_sprint.name}.",
                epic_owner=True,
            )


@celery_app.task(ignore_result=True)
def check_tickets_ready_for_sprint_task() -> None:
    """Notify team members about incomplete tickets."""
    with connect_to_jira() as conn:
        cell_membership = get_cell_membership(conn)
        issues = get_next_sprint_issues(conn)

        for user, incomplete_issues in group_incomplete_issues(conn, issues).items():
            # TODO: Add more flexibility to the Mattermost library, to support a nicer format here.
            message = f"{settings.SPRINT_ASYNC_INCOMPLETE_TICKET_MESSAGE}{incomplete_issues}"
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


@celery_app.task(ignore_result=True)
def create_estimation_session_task() -> None:
    """
    Create a new empty estimation session for every cell.

    An empty estimation session does not contain any issues or participants. The current user is added as the scrum
    master of the session, as without this permission it wouldn't be possible to make any future modifications.

    WARNING
    Creating a session without issues causes some chaos in Jira, as the `/session/async/{sessionId}/rounds/` endpoint
    returns HTTP 500 in such case. It does not break other API calls, so operations like updating, closing, and deleting
    the session (via the API) work correctly. It makes the session unusable via the browser by breaking two views:
        - estimation,
        - configuration.
    Therefore, the decision is to avoid adding the participants to the session until there are issues that can be added
    too. Assuming that the sessions are fully automated, and don't require any manual interventions in the beginning,
    this should not cause any troubles.
    """
    with connect_to_jira() as conn:
        session_name = get_next_poker_session_name(conn)
        for cell in get_cells(conn):
            if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
                conn.create_poker_session(
                    board_id=cell.board_id,
                    name=session_name,
                    issues=[],
                    participants=[],
                    scrum_masters=[conn.myself()['key']],
                    send_invitations=False,
                )


@celery_app.task(ignore_result=True)
def update_estimation_session_task() -> None:
    """
    Update estimation session's issues and participants.

    If no issues exist for the session, then it will not be updated. The reasoning behind this has been described in the
    `create_estimation_session_task` function.

    This does not override the manual additions to the session - i.e. if an issue or user has been added manually to the
    session, then it will be retained, as it merges available issues and participants with the applied ones.
    However, any removed items (e.g. an issue scheduled for the next sprint, or a user who is a member of the cell)
    will be added back automatically.

    FIXME: This adds all cell members as scrum masters to the session, because at the moment we do not have a way to
           determine whether the member is a part of the core team. We can restrict this in the future, if needed.
    """
    with connect_to_jira() as conn:
        session_name = get_next_poker_session_name(conn)
        issues = get_unestimated_next_sprint_issues(conn)
        # FIXME: This will not work for more than 1000 users. To support it, add `startAt` to handle the pagination.
        all_users = conn.search_users("''", maxResults=1000)  # Searching for the "quotes" returns all users.

        for cell in get_cells(conn):
            try:
                poker_session = conn.poker_sessions(cell.board_id, state="OPEN", name=session_name)[0]
            except IndexError:
                if not settings.DEBUG:
                    # It can happen:
                    # 1. When this runs before the `create_estimation_session_task`, e.g. when the sprint is created
                    #    manually a moment before the full hour.
                    # 2. If a new cell has been added, then its session was created manually, and it either:
                    #    - does not have a correct name,
                    #    - does not have the Jira bot added as its scrum master.
                    # noinspection PyUnresolvedReferences
                    from sentry_sdk import capture_message

                    capture_message(
                        f"Could not find a session called {session_name} in {cell.name}. If you haven't completed the "
                        f"sprint yet, then you should consider adjusting the start time of this task, so it's started "
                        f"only once the new sprint has been started. If this is a new cell, please make sure that an "
                        f"estimation session with this name exists and {settings.JIRA_BOT_USERNAME} has been added as "
                        f"a scrum master there."
                    )
                continue

            # Get IDs of issues belonging only to a specific cell.
            cell_issue_ids = set(issue.id for issue in issues if issue.key.startswith(cell.key))
            current_issue_ids = set(conn.poker_session_results(poker_session.sessionId).keys())
            all_issue_ids = list(current_issue_ids | cell_issue_ids)
            if all_issue_ids:
                # User's `name` and `key` are not always the same.
                members = get_cell_member_names(conn, get_cell_members(conn.quickfilters(cell.board_id)))
                member_keys = set(user.key for user in all_users if user.displayName in members)

                current_member_keys = set(user.userKey for user in poker_session.participants)
                current_scrum_master_keys = set(user.userKey for user in poker_session.scrumMasters)

                all_member_keys = list(current_member_keys | member_keys)
                all_scrum_master_keys = list(current_scrum_master_keys | member_keys)

                if not settings.DEBUG:  # We don't want to trigger this in the dev environment.
                    # TODO: Handle 403 response when the bot is not added as a participant.
                    poker_session.update(
                        {
                            'issuesIds': all_issue_ids,
                            'participants': all_member_keys,
                            'scrumMasters': all_scrum_master_keys,
                            'sendInvitations': False,  # TODO: This should notify participants in case of any changes.
                        }
                    )


@celery_app.task(ignore_result=True)
def close_estimation_session_task() -> None:
    """
    Close all "next-sprint" estimation sessions for every cell.

    The "next-sprint" estimation session needs to match the following criteria:
    - is open,
    - has the name matching the result of the `get_next_poker_session_name` function.
    """
    with connect_to_jira() as conn:
        session_name = get_next_poker_session_name(conn)

        for cell in get_cells(conn):
            poker_sessions = conn.poker_sessions(cell.board_id, state="OPEN", name=session_name)
            if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
                # Handle closing multiple sessions with the same name (though it should not happen).
                for session in poker_sessions:
                    conn.close_poker_session(session.sessionId, send_notifications=True)

    move_estimates_to_tickets_task.delay()


@celery_app.task(ignore_result=True)
def move_estimates_to_tickets_task() -> None:
    """
    Applies the average vote results from the closed estimation session to the tickets for every cell.

    If there were no votes for a specific issue, its assignee (or another responsible person) is notified.
    """
    with connect_to_jira() as conn:
        session_name = get_next_poker_session_name(conn)

        for cell in get_cells(conn):
            vote_values = conn.poker_session_vote_values(cell.board_id)
            poker_sessions = conn.poker_sessions(cell.board_id, state="CLOSED", name=session_name)

            if not poker_sessions and not settings.DEBUG:
                # This can happen if a new cell has been added, then its session was created manually, and it either:
                # - does not have a correct name,
                # - does not have the Jira bot added as its scrum master.
                # noinspection PyUnresolvedReferences
                from sentry_sdk import capture_message

                capture_message(
                    f"Could not find a session called {session_name} in {cell.name}. If this is a new cell, please "
                    f"make sure that an estimation session with this name exists and {settings.JIRA_BOT_USERNAME} "
                    f"has been added as a scrum master there."
                )

            # Handle applying the results from multiple sessions with the same name (though it should not happen).
            for session in poker_sessions:
                for issue, results in conn.poker_session_results(session.sessionId).items():
                    votes = []
                    for result in results.values():
                        vote = result.get("selectedVote")
                        if str(vote).replace('.', '', 1).isdigit():  # Ignore non-numeric answers.
                            votes.append(float(vote))  # type: ignore

                    try:
                        final_vote = get_poker_session_final_vote(votes, vote_values)
                    except AttributeError:  # No votes.
                        ping_users_on_ticket(conn, conn.issue(issue), settings.SPRINT_ASYNC_POKER_NO_ESTIMATES_MESSAGE)
                    else:
                        if not settings.DEBUG:  # We really don't want to trigger this in the dev environment.
                            conn.update_issue(
                                issue, conn.issue_fields[settings.JIRA_FIELDS_STORY_POINTS], str(final_vote)
                            )
