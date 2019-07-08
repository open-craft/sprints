import re
from contextlib import contextmanager
from typing import (
    ContextManager,
    Dict,
    List,
    Union,
)

from google.oauth2 import service_account
from googleapiclient import discovery

from config.settings.base import (
    GOOGLE_API_CREDENTIALS,
    GOOGLE_CALENDAR_VACATION_REGEX,
)


@contextmanager
def connect_to_google() -> ContextManager[discovery.Resource]:
    """Connects to Google API with service account."""
    scopes = ['https://www.googleapis.com/auth/calendar']
    credentials = service_account.Credentials.from_service_account_info(GOOGLE_API_CREDENTIALS, scopes=scopes)
    service = discovery.build('calendar', 'v3', credentials=credentials)
    yield service


def get_vacations(from_: str, to: str) -> List[Dict[str, Union[str, Dict[str, str]]]]:
    """Retrieves user's vacations from Google Calendar."""
    with connect_to_google() as conn:
        calendars = [item['id'] for item in conn.calendarList().list(fields='items(id)').execute()['items']]
        vacations = []
        for calendar in calendars:
            events = conn.events().list(
                calendarId=calendar,
                timeZone='Europe/London',
                timeMin=f'{from_}T00:00:00Z',
                timeMax=f'{to}T00:00:00Z',
                fields='items(end/date, start/date, summary)'
            ).execute()

            for event in events['items']:
                try:
                    user = re.match(GOOGLE_CALENDAR_VACATION_REGEX, event['summary'], re.IGNORECASE).group(1)
                    del event['summary']
                    event['user'] = user
                    vacations.append(event)
                except AttributeError:
                    # Ignore non-matching events.
                    pass

        vacations.sort(key=lambda x: x['user'])  # Small optimization for searching
        return vacations
