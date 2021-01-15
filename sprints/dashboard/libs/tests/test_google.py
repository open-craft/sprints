import re

import pytest
from django.conf import settings


@pytest.mark.parametrize(
    "calendar_event, expected_name, expected_action, expected_hours",
    [
        ('John off', 'John', 'off', None),  # Deprecated format.
        ('John Doe off', 'John', 'Doe off', None),  # Deprecated format.
        ('John 3h', 'John', '', '3'),  # Deprecated format.
        ('John available 3h/day', 'John', 'available ', '3'),  # Deprecated format.
        ('John: off', 'John', 'off', None),
        ('John Doe: off', 'John Doe', 'off', None),
        ('John Doe: 3h', 'John Doe', '', '3'),
        ('John Doe: available 3h/day', 'John Doe', 'available ', '3'),
    ],
)
def test_vacation_format(calendar_event, expected_name, expected_action, expected_hours):
    regex = settings.GOOGLE_CALENDAR_VACATION_REGEX
    search = re.match(regex, calendar_event, re.IGNORECASE).groupdict()

    assert search.get('name') or search.get('first_name') == expected_name
    assert search.get('action') == expected_action
    assert search.get('hours') == expected_hours
