import datetime

import pytest

from sustainability.utils import (
    diff_month,
    generate_month_range,
)


@pytest.mark.parametrize(
    "start, end, expected", [
        ("2020-1-1", "2020-2-1", 2),
        ("2019-12-1", "2020-2-1", 3),
        ("2020-1-1", "2020-1-31", 1),
    ]
)
def test_generate_month_range(start, end, expected):
    assert len(list(generate_month_range(start, end))) == expected


@pytest.mark.parametrize(
    "start, end, expected", [
        (datetime.date(2020, 1, 1), datetime.date(2020, 1, 1), 1),
        (datetime.date(2020, 1, 1), datetime.date(2020, 1, 31), 1),
        (datetime.date(2020, 1, 1), datetime.date(2020, 2, 1), 2),
        (datetime.date(2019, 12, 1), datetime.date(2020, 2, 1), 3),
    ]
)
def test_diff_month(start, end, expected):
    assert diff_month(start, end) == expected


def test_diff_month_start_after_end():
    with pytest.raises(AttributeError):
        diff_month(datetime.date(2020, 1, 2), datetime.date(2020, 1, 1))
