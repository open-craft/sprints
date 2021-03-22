import json
from contextlib import contextmanager
from functools import cached_property
from typing import (
    Dict,
    Iterator,
    List,
)

from django.conf import settings
from jira import JIRA
from jira.client import ResultList
from jira.exceptions import JIRAError
from jira.resources import (
    GreenHopperResource,
    Resource,
    Worklog,
)
from jira.utils import json_loads


class QuickFilter(GreenHopperResource):
    """Class for representing Jira quickfilter resource."""

    def __init__(self, options, session, raw=None):
        GreenHopperResource.__init__(self, 'quickfilter/{0}', options, session, raw)


class Schedule(Resource):
    """Class for representing Tempo schedule resource."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'schedule/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Account(Resource):
    """Class for representing Tempo Account resource."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'account/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Expense(Resource):
    """Class for representing Tempo Expense resource."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'expense/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Report(Resource):
    """Class for representing Tempo Report resource."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'report/{0}', options, session)
        if raw:
            self._parse_raw(raw)


class Poker(Resource):
    """Class for representing Agile Poker session resource."""

    def __init__(self, options, session, raw=None):
        Resource.__init__(self, 'pokerng/{0}', options, session)
        if raw:
            self._parse_raw(raw)

        # Specify the API for the poker session.
        self._session.headers['content-type'] = 'application/json'
        options = self._options.copy()
        options.update(
            {
                'rest_path': 'pokerng',
                'rest_api_version': '1.0',
                # HACK: The `?withUserKeys=true` querystring is used only with `PUT` requests, but the Jira library does
                #  not allow adding custom data to the URL, so we're using this with all types of requests.
                #  It could be possible to avoid using this, but this API is undocumented and it would require some
                #  guessing how users should be passed within a request.
                'path': f'session/id/{self.sessionId}?withUserKeys=true',
            }
        )
        # This attribute is used by the superclass for querying the API.
        self.self = self._base_url.format(**options)

    def update(
        self,
        fields: dict[str, object] = None,
        async_: bool = None,
        jira: 'CustomJira' = None,
        notify: bool = True,
        **kwargs,
    ):
        """
        Update this poker session on the server.

        :param fields: Fields which should be updated for the object.
        :param async_: If true the request will be added to the queue so it can be executed later using async_run().
        :param jira: Instance of the JIRA Client.
        :param notify: Whether or not to notify participants about the update via email. (Default: True).
        """
        issues = []
        fields = fields or {}
        if 'issuesIds' not in fields:
            # This way we don't need to run the `poker_session_results` method twice or include the jira connection when
            # it is not necessary.
            if jira:
                issues = list(jira.poker_session_results(self.sessionId).keys())
            else:
                raise AttributeError(
                    "You should either specify `issueIds` in the `fields` or provide a Jira client in "
                    "`kwargs` to update the poker session."
                )

        # All these fields need to be present in the `PUT` request.
        data = {
            'name': self.name,
            'estimationFieldId': self.estimationFieldId,
            'mode': self.mode,
            'participants': [u.userKey for u in self.participants],
            'scrumMasters': [u.userKey for u in self.scrumMasters],
            'issuesIds': issues,
            'sendInvitations': notify,
        }
        data.update(fields)

        super().update(data, async_, jira, notify, **kwargs)


class CustomJira(JIRA):
    """Custom Jira class for using greenhopper and Tempo APIs."""

    AGILE_POKER_URL = '{server}/rest/pokerng/1.0/{path}'
    API_V2 = '{server}/rest/api/2/{path}'
    GREENHOPPER_BASE_URL = '{server}/rest/greenhopper/1.0/{path}'
    TEMPO_CORE_URL = '{server}/rest/tempo-core/1/{path}'
    TEMPO_ACCOUNTS_URL = '{server}/rest/tempo-accounts/1/{path}'
    TEMPO_TIMESHEETS_URL = '{server}/rest/tempo-timesheets/3/{path}'

    def move_to_backlog(self, issue_keys: list[str]):
        """
        It is not mentioned in Python lib docs, but the limit for the issue-moving queries is 50 issues. Source:
        https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-backlog-issue-post
        """
        batch_size = 50
        for chunk in chunks(issue_keys, batch_size):
            super().move_to_backlog(chunk)

    def add_issues_to_sprint(self, sprint_id: int, issue_keys: list[str]):
        """
        It is not mentioned in Python lib docs, but the limit for the issue-moving queries is 50 issues. Source:
        https://developer.atlassian.com/cloud/jira/software/rest/#api-rest-agile-1-0-sprint-sprintId-issue-post
        """
        batch_size = 50
        for chunk in chunks(issue_keys, batch_size):
            super().add_issues_to_sprint(sprint_id, chunk)

    def quickfilters(self, board_id: int) -> ResultList:
        """Retrieve quickfilters defined for the board with `board_id`."""
        r_json = self._get_json(f'gadgets/rapidview/pool/quickfilters/{board_id}', base=self.GREENHOPPER_BASE_URL)
        filters = [QuickFilter(self._options, self._session, raw_quickfilters_json) for raw_quickfilters_json in r_json]
        return ResultList(filters, 0, len(filters), len(filters), True)

    def user_schedule(self, user: str, from_: str, to: str) -> Schedule:
        """
        Retrieve `user`'s commitments `from_` the date `to` another date (both inclusive).
        The date format for `from_` and `to` is `%Y-%m-%d`.
        """
        r_json = self._get_json(f'user/schedule?user={user}&from={from_}&to={to}', base=self.TEMPO_CORE_URL)
        schedule = Schedule(self._options, self._session, r_json)
        return schedule

    def accounts(self, skip_archived: bool = True) -> ResultList:
        """Retrieve accounts from the Tempo plugin."""
        r_json = self._get_json(f'account?skipArchived={skip_archived}', base=self.TEMPO_ACCOUNTS_URL)
        accounts = [Account(self._options, self._session, raw_accounts_json) for raw_accounts_json in r_json]
        return ResultList(accounts, 0, len(accounts), len(accounts), True)

    def expenses(self, account_id: int, from_: str, to: str) -> Expense:
        """
        Retrieve worklogs for the selected account `from_` the date `to` another date (both inclusive).
        The date format for `from_` and `to` is `%Y-%M-%d`.
        """
        r_json = self._get_json(
            f'report/account/{account_id}/timeandexpenses?dateFrom={from_}&dateTo={to}',
            base=self.TEMPO_TIMESHEETS_URL,
        )
        expenses = Expense(self._options, self._session, r_json)
        return expenses

    def report(self, from_: str, to: str) -> Report:
        """
        Retrieves team worklogs `from_` the date `to` another date (both inclusive).
        The date format for `from_` and `to` is `%Y-%M-%d`.
        """
        r_json = self._get_json(
            f'report/team/{settings.TEMPO_TEAM_ID}/utilization?dateFrom={from_}&dateTo={to}',
            base=self.TEMPO_TIMESHEETS_URL,
        )
        report = Report(self._options, self._session, r_json)
        return report

    def worklog_list(self, worklogs: List[int]) -> List[Worklog]:
        """
        Retrieves list of worklogs with IDs provided in the request's body.

        Limited to 1000 worklogs. Source:
        https://developer.atlassian.com/cloud/jira/platform/rest/v3/?utm_source=%2Fcloud%2Fjira%2Fplatform%2Frest%2F&utm_medium=302#api-rest-api-3-worklog-list-post
        """
        aggregated_worklogs: List[Dict] = []
        for chunk in chunks(worklogs, 1000):
            r_json = self._session.post(
                url=self._get_url('worklog/list', self.API_V2),
                data=json.dumps({'ids': chunk}),
            )
            aggregated_worklogs.extend(json.loads(r_json.text))

        worklogs = [Worklog(self._options, self._session, raw_worklog_json) for raw_worklog_json in aggregated_worklogs]
        return worklogs

    def poker_sessions(self, board_id: int, state: str = None, name: str = None) -> list[Poker]:
        """
        Retrieve agile poker sessions from the specific board, optionally filtered by their state and name.

        :param board_id: The board to get sessions from.
        :param state: Filter results by specified states. Valid values: "OPEN", "CLOSED".
        :param name: Filter results by their names.
        :return: A list of sessions.
        """
        r_json = self._get_json(f'session/board/{board_id}', base=self.AGILE_POKER_URL)
        sessions = [Poker(self._options, self._session, raw_sessions_json) for raw_sessions_json in r_json]
        if state:
            sessions = list(filter(lambda s: s.state == state, sessions))
        if name:
            sessions = list(filter(lambda s: s.name == name, sessions))
        return sessions

    def poker_session(self, session_id: int) -> Poker:
        """
        Retrieve the agile poker session by its ID.

        :param session_id: The ID of the session to get.
        :return: A session.
        """
        r_json = self._get_json(f'session/id/{session_id}', base=self.AGILE_POKER_URL)
        return Poker(self._options, self._session, r_json)

    def create_poker_session(
        self,
        board_id: int,
        name: str,
        issues: list[str],
        participants: list[str],
        scrum_masters: list[str],
        send_invitations: bool = True,
    ) -> Poker:
        """
        Create a new agile poker session.

        :param board_id: The board to get sessions from.
        :param name: Name of the session.
        :param scrum_masters: A list of participants with scrum masters permissions.
        :param participants: A list of standard participants of the session.
        :param issues: A list of issues to be estimated in a session.
        :param send_invitations: Whether or not to notify participants about the update via email. (Default: True).
        :return: A new session.
        """
        response = self._session.post(
            url=self._get_url(f'session/async?boardId={board_id}', self.AGILE_POKER_URL),
            headers={'content-type': 'application/json'},
            data=json.dumps(
                {
                    'estimationFieldId': self.issue_fields[settings.JIRA_FIELDS_STORY_POINTS],
                    'invitationMessage': settings.SPRINT_ASYNC_POKER_NEW_SESSION_MESSAGE,
                    'name': name,
                    'issueIds': issues,
                    'participantsUserKeys': participants,
                    'scrumMastersUserKeys': scrum_masters,
                    'sendInvitations': send_invitations,
                }
            ),
        )
        return Poker(self._options, self._session, json_loads(response))

    def close_poker_session(self, session_id: int, send_notifications: bool = True) -> Poker:
        """
        Close an agile poker session.

        :param session_id: The ID of the session to close.
        :param send_notifications: Whether or not to notify participants about the update via email. (Default: True).
        :return: A closed session.
        """
        response = self._session.put(
            url=self._get_url(f'session/async/{session_id}/rounds/latest', self.AGILE_POKER_URL),
            headers={'content-type': 'application/json'},
            data=json.dumps(
                {
                    'closeRound': True,
                    'sendCloseNotifications': send_notifications,
                }
            ),
        )
        return Poker(self._options, self._session, json_loads(response))

    def poker_session_vote_values(self, board_id: int) -> list[float]:
        """
        Retrieve a list of possible vote values, configured per board.

        :param board_id: The board to get possible values from.
        :return: A list of possible vote values.
        """
        response = self._get_json(f'board/{board_id}/settings', base=self.AGILE_POKER_URL)
        return [
            float(vote['value'])
            for vote in response.get('voteValues', [])
            if vote['value'].replace('.', '', 1).isdigit()
        ]

    def poker_session_results(self, session_id: int) -> dict[str, dict[str, dict[str, object]]]:
        """
        Retrieve agile poker session's results.

        :param session_id: The ID of the session to get results from.
        :return: A dict containing results of the session. It has the following structure:
                 {
                    'issue_id': {
                        'user_key': {
                            'userKey': 'user_key' (str),
                            'hasVoted': True (bool),
                            'canSeeIssue': True (bool),
                            'selectedVote': '1' (str, can be non-numeric, e.g. '?'),
                            'voteComment': 'comment' (str),
                            'issueId': issue_id (int)
                        }
                    }
                }
        """
        try:
            response = self._get_json(f'session/async/{session_id}/rounds/latest', base=self.AGILE_POKER_URL)
        except JIRAError:
            response = {}

        return response.get('issueVotes', {})

    def update_issue(self, issue: str, field_id: str, value: str) -> None:
        """
        Update a specific field of the Jira issue.

        :param issue: Issue key or ID.
        :param field_id: An ID of the field that will be updated.
        :param value: A new value of the field.
        """
        self._session.put(
            url=self._get_url(f'xboard/issue/update-field.json', self.GREENHOPPER_BASE_URL),
            headers={'content-type': 'application/json'},
            data=json.dumps(
                {
                    'issueIdOrKey': issue,
                    'fieldId': field_id,
                    'newValue': value,
                }
            ),
        )

    @cached_property
    def issue_fields(self) -> Dict[str, str]:
        """Get issue field names mapped to their IDs."""
        field_ids = {field['name']: field['id'] for field in self.fields()}
        required_fields = set(
            settings.JIRA_REQUIRED_FIELDS + settings.SPILLOVER_REQUIRED_FIELDS + settings.JIRA_AUTOMATION_FIELDS
        )
        return {field: field_ids[field] for field in required_fields}


@contextmanager
def connect_to_jira() -> Iterator[CustomJira]:
    """Context manager for establishing connection with Jira server."""
    conn = CustomJira(
        server=settings.JIRA_SERVER,
        basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD),
        options={
            'agile_rest_path': GreenHopperResource.AGILE_BASE_REST_PATH,
            'headers': {
                # Ugly hack, but the Agile Poker REST API returns HTTP 403 without this.
                'Referer': f'{settings.JIRA_SERVER}'
                f'/download/resources/com.spartez.jira.plugins.jiraplanningpoker/frontend/index.html',
                'content-type': 'application/json',
            },
        },
    )
    yield conn
    conn.close()


def chunks(lst: List, n: int) -> Iterator[List]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
