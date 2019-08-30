from contextlib import contextmanager
from typing import (
    Iterator,
)

from django.conf import settings
from jira import JIRA
from jira.client import ResultList
from jira.resources import (
    GreenHopperResource,
    Resource,
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


class CustomJira(JIRA):
    """Custom Jira class for using greenhopper and Tempo APIs."""
    GREENHOPPER_BASE_URL = '{server}/rest/greenhopper/1.0/{path}'
    TEMPO_BASE_URL = '{server}/rest/tempo-core/1/{path}'

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
        r_json = self._get_json(f'user/schedule?user={user}&from={from_}&to={to}', base=self.TEMPO_BASE_URL)
        schedule = Schedule(self._options, self._session, r_json)
        return schedule


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
