import json
from contextlib import contextmanager
from typing import (
    Dict,
    Iterator,
    List,
)

from django.conf import settings
from jira import JIRA
from jira.client import ResultList
from jira.resources import (
    GreenHopperResource,
    Resource,
    Worklog,
)


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


class CustomJira(JIRA):
    """Custom Jira class for using greenhopper and Tempo APIs."""
    API_V2 = '{server}/rest/api/2/{path}'
    GREENHOPPER_BASE_URL = '{server}/rest/greenhopper/1.0/{path}'
    TEMPO_CORE_URL = '{server}/rest/tempo-core/1/{path}'
    TEMPO_ACCOUNTS_URL = '{server}/rest/tempo-accounts/1/{path}'
    TEMPO_TIMESHEETS_URL = '{server}/rest/tempo-timesheets/3/{path}'

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

        worklogs = [Worklog(self._options, self._session, raw_worklog_json)
                    for raw_worklog_json in aggregated_worklogs]
        return worklogs


@contextmanager
def connect_to_jira() -> Iterator[CustomJira]:
    """Context manager for establishing connection with Jira server."""
    conn = CustomJira(
        server=settings.JIRA_SERVER,
        basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD),
        options={'agile_rest_path': GreenHopperResource.AGILE_BASE_REST_PATH}
    )
    yield conn
    conn.close()


def chunks(lst: List, n: int) -> Iterator[List]:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
