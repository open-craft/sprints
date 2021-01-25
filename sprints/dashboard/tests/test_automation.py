from unittest.mock import patch

import pytest
from dateutil.parser import parse
from freezegun import freeze_time

from sprints.dashboard.automation import (
    get_current_sprint_day,
    get_specific_day_of_sprint,
)


@patch("sprints.dashboard.automation.get_current_sprint_start_date")
@pytest.mark.parametrize(
    "test_date, expected",
    [
        ("2020-10-18", -1),
        ("2020-10-19", 0),
        ("2020-10-21", 2),
        ("2020-11-02", 14),
        ("2020-11-12", 24),
    ],
)
def test_get_current_sprint_day(get_sprint_start_date, test_date, expected):
    get_sprint_start_date.return_value = "2020-10-20"
    with freeze_time(test_date):
        assert get_current_sprint_day() == expected


@patch("sprints.dashboard.automation.get_current_sprint_start_date")
@pytest.mark.parametrize(
    "day, expected_date",
    [
        (-1, parse("2020-10-18")),
        (0, parse("2020-10-19")),
        (2, parse("2020-10-21")),
        (14, parse("2020-11-02")),
        (24, parse("2020-11-12")),
    ],
)
def test_get_specific_day_of_sprint(get_sprint_start_date, day, expected_date):
    get_sprint_start_date.return_value = "2020-10-20"
    assert get_specific_day_of_sprint(day) == expected_date
