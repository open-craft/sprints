import pytest
from django.conf import settings

from sprints.dashboard.models import DashboardIssue
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
def test_get_sprint_meeting_day_division_for_member(test_description, test_directive, expected, raises):
    mock_issue = object.__new__(DashboardIssue)
    mock_issue.description = test_description

    with raises:
        assert mock_issue.get_bot_directive(test_directive) == expected
