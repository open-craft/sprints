import re
from contextlib import contextmanager
from typing import (
    Dict,
    Iterator,
    List,
    Union,
)

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient import discovery


@contextmanager
def connect_to_google(service: str) -> Iterator[discovery.Resource]:
    """Connects to Google API with service account."""
    scopes = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/spreadsheets',
    ]
    credentials = service_account.Credentials.from_service_account_info(settings.GOOGLE_API_CREDENTIALS, scopes=scopes)
    api_version = {
        'calendar': 'v3',
        'sheets': 'v4',
    }
    try:
        service = discovery.build(service, api_version[service], credentials=credentials, cache_discovery=False)
    except KeyError:
        raise AttributeError("Unknown service name.")
    yield service


def get_vacations(from_: str, to: str) -> List[Dict[str, Union[str, Dict[str, str]]]]:
    """Retrieves user's vacations from Google Calendar."""
    with connect_to_google('calendar') as conn:
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
                user_search = re.match(settings.GOOGLE_CALENDAR_VACATION_REGEX, event['summary'], re.IGNORECASE)
                # Only `All day` events are taken into account.
                if user_search and {'start', 'end'} <= event.keys():
                    user = user_search.group(1)
                    del event['summary']
                    event['user'] = user
                    vacations.append(event)

        vacations.sort(key=lambda x: x['user'])  # Small optimization for searching
        return vacations


def upload_spillovers(spillovers: List[List[str]]) -> None:
    """Uploads the prepared rows to Google spreadsheet."""
    with connect_to_google('sheets') as conn:
        sheet = conn.spreadsheets()
        body = {'values': spillovers}
        sheet.values().append(
            spreadsheetId=settings.GOOGLE_SPILLOVER_SPREADSHEET,
            range='Spillovers',
            body=body,
            valueInputOption='USER_ENTERED',
        ).execute()


def get_commitments_spreadsheet(cell_name: str) -> List[List[str]]:
    """Retrieve the current commitment spreadsheet."""
    with connect_to_google('sheets') as conn:
        sheet = conn.spreadsheets()
        return sheet.values().get(
            spreadsheetId=settings.GOOGLE_SPILLOVER_SPREADSHEET,
            range=f"'{cell_name} Commitments'!A3:ZZZ999",
            majorDimension='COLUMNS',
        ).execute()['values']


def upload_commitments(users: List[str], commitments: List[str], range_: str) -> None:
    """Upload new members and commitments to the spreadsheet."""
    with connect_to_google('sheets') as conn:
        sheet = conn.spreadsheets()
        users_body = {
            'values': [users],
            'majorDimension': 'COLUMNS',
        }
        sheet.values().append(
            spreadsheetId=settings.GOOGLE_SPILLOVER_SPREADSHEET,
            range=range_.split('!')[0],
            body=users_body,
            valueInputOption='USER_ENTERED',
        ).execute()

        body = {
            'values': [commitments],
            'majorDimension': 'COLUMNS'
        }
        sheet.values().append(
            spreadsheetId=settings.GOOGLE_SPILLOVER_SPREADSHEET,
            range=range_,
            body=body,
            valueInputOption='USER_ENTERED',
        ).execute()


def get_rotations_spreadsheet() -> List[List[str]]:
    """Retrieve the current rotations spreadsheet."""
    with connect_to_google('sheets') as conn:
        sheet = conn.spreadsheets()
        return sheet.values().get(
            spreadsheetId=settings.GOOGLE_ROTATIONS_SPREADSHEET,
            range=settings.GOOGLE_ROTATIONS_RANGE,
            majorDimension='COLUMNS',
        ).execute()['values']


def get_rotations_users(sprint_number: str, cell_name: str) -> Dict[str, List[str]]:
    """Retrieve users that have cell roles assigned for the chosen sprint."""
    spreadsheet = get_rotations_spreadsheet()
    sprint_rows: List[int] = []
    for i, row in enumerate(spreadsheet[0]):
        if row.startswith(sprint_number):
            sprint_rows.append(i)

    result: Dict[str, List[str]] = {}
    for column in spreadsheet:
        if column[0].startswith(cell_name):
            role_name = column[0].replace(cell_name, '').strip()
            result[role_name] = []
            for row in sprint_rows:  # type: ignore
                if column[row]:  # type: ignore
                    result[role_name].append(column[row])  # type: ignore

    return result


def get_availability_spreadsheet() -> List[List[str]]:
    """Retrieve the availability spreadsheet."""
    with connect_to_google('sheets') as conn:
        sheet = conn.spreadsheets()
        return sheet.values().get(
            spreadsheetId=settings.GOOGLE_CONTACT_SPREADSHEET,
            range=settings.GOOGLE_AVAILABILITY_RANGE,
            majorDimension='ROWS',
        ).execute()['values']
