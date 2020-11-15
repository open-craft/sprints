import pytest
from django.conf import settings

from sprints.dashboard.models import (
    Dashboard,
    DashboardIssue,
)
from sprints.dashboard.tests.helpers import does_not_raise


@pytest.mark.parametrize(
    "test_description, test_directive, expected, raises",
    [
        (
            'Test [~crafty]: plan 1 hours 1 minutes per sprint for this task',
            settings.SPRINT_RECURRING_DIRECTIVE,
            3660,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 3h10m per sprint for this task',
            settings.SPRINT_RECURRING_DIRECTIVE,
            11400,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan  10m per sprint for this task',
            settings.SPRINT_RECURRING_DIRECTIVE,
            600,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 3h       10m per sprint for this task',
            settings.SPRINT_RECURRING_DIRECTIVE,
            11400,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 3h 10m per sprint for this task',
            settings.SPRINT_RECURRING_DIRECTIVE,
            11400,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 1 hour 1 minute per sprint for this task',
            settings.SPRINT_RECURRING_DIRECTIVE,
            3660,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 5hous 10minutes per sprint for this task',  # Test with a typo.
            settings.SPRINT_RECURRING_DIRECTIVE,
            18600,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 5h 10m per sprint for epic management',
            settings.SPRINT_EPIC_DIRECTIVE,
            18600,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 5 hours for reviewing this task',
            settings.SPRINT_REVIEW_DIRECTIVE,
            18000,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 10 minutes for reviewing this task',
            settings.SPRINT_REVIEW_DIRECTIVE,
            600,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan 5hrs 10mins per sprint for this task',  # Directive not found.
            settings.SPRINT_REVIEW_DIRECTIVE,
            18600,
            pytest.raises(ValueError),
        ),
        (
            None,  # Description is `None`.
            settings.SPRINT_REVIEW_DIRECTIVE,
            18600,
            pytest.raises(ValueError),
        ),
        (
            'Test [~crafty]: plan  per sprint for this task',  # Value not provided. Known, but safe to ignore.
            settings.SPRINT_RECURRING_DIRECTIVE,
            0,
            does_not_raise(),
        ),
        (
            'Test [~crafty]: plan per sprint for this task',  # Value not provided.
            settings.SPRINT_RECURRING_DIRECTIVE,
            0,
            pytest.raises(ValueError),
        ),
    ],
)
def test_get_bot_directive(test_description, test_directive, expected, raises):
    mock_issue = object.__new__(DashboardIssue)
    mock_issue.description = test_description

    with raises:
        assert mock_issue.get_bot_directive(test_directive) == expected


@pytest.mark.parametrize(
    "commitments, date, planned_commitments, username, division, expected",
    [
        # For positive timezone the day before sprint starts is within the previous sprint, so division is ignored.
        (28800, "2020-11-16", 28700, "x", {"x": (0.6, True)}, 0),
        # For negative timezone the day before sprint can span two sprints...
        (28800, "2020-11-16", 28700, "x", {"x": (0.4, False)}, 60),
        # ...but it does not need to do so.
        (28800, "2020-11-16", 28700, "x", {"x": (0, False)}, 100),
        # For the positive timezone the first day of the sprint may span two sprints.
        (28800, "2020-11-17", 28700, "x", {"x": (0.6, True)}, 40),
        # For the negative timezone the first day of the sprint is only in a single sprint.
        (28800, "2020-11-17", 28700, "x", {"x": (0.4, False)}, 100),
        # For the positive timezone the last day of the sprint is only in a single sprint.
        (28800, "2020-11-30", 28700, "x", {"x": (0.6, True)}, 100),
        # For the negative timezone the last day of the sprint can span two sprints.
        (28800, "2020-11-30", 28700, "x", {"x": (0.4, False)}, 40),
        # For the positive timezone the day after last day of the sprint can span two sprints...
        (28800, "2020-12-1", 28700, "x", {"x": (0.6, True)}, 60),
        # ... but it does not need to do so.
        (28800, "2020-12-1", 28700, "x", {"x": (0, True)}, 0),
        # For the negative timezone the last day of the sprint is only in a single sprint.
        (28800, "2020-12-1", 28700, "x", {"x": (0.4, False)}, 0),
        # Standard cases - vacations scheduled in the middle of the sprint.
        (28800, "2020-11-20", 28700, "x", {"x": (0.4, False)}, 100),
        (28800, "2020-11-20", 28700, "x", {"x": (0.4, True)}, 100),
    ],
)
def test_get_vacation_for_day(commitments, date, planned_commitments, username, division, expected):
    mock_dashboard = object.__new__(Dashboard)
    mock_dashboard.future_sprint_start = "2020-11-17"
    mock_dashboard.future_sprint_end = "2020-11-30"
    mock_dashboard.sprint_division = division

    assert mock_dashboard._get_vacation_for_day(commitments, date, planned_commitments, username) == expected
