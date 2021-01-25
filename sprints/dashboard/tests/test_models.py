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
            "Test [~crafty]: plan 1 hours 1 minutes per sprint for this task",
            settings.SPRINT_RECURRING_DIRECTIVE,
            3660,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 3h10m per sprint for this task",
            settings.SPRINT_RECURRING_DIRECTIVE,
            11400,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan  10m per sprint for this task",
            settings.SPRINT_RECURRING_DIRECTIVE,
            600,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 3h       10m per sprint for this task",
            settings.SPRINT_RECURRING_DIRECTIVE,
            11400,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 3h 10m per sprint for this task",
            settings.SPRINT_RECURRING_DIRECTIVE,
            11400,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 1 hour 1 minute per sprint for this task",
            settings.SPRINT_RECURRING_DIRECTIVE,
            3660,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 5hous 10minutes per sprint for this task",  # Test with a typo.
            settings.SPRINT_RECURRING_DIRECTIVE,
            18600,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 5h 10m per sprint for epic management",
            settings.SPRINT_EPIC_DIRECTIVE,
            18600,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 5 hours for reviewing this task",
            settings.SPRINT_REVIEW_DIRECTIVE,
            18000,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 10 minutes for reviewing this task",
            settings.SPRINT_REVIEW_DIRECTIVE,
            600,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan 5hrs 10mins per sprint for this task",  # Directive not found.
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
            "Test [~crafty]: plan  per sprint for this task",  # Value not provided. Known, but safe to ignore.
            settings.SPRINT_RECURRING_DIRECTIVE,
            0,
            does_not_raise(),
        ),
        (
            "Test [~crafty]: plan per sprint for this task",  # Value not provided.
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
        # 1. Day before the end of the sprint.
        # ====================================
        # a. Positive timezone.
        # ---------------------
        # It is within the previous sprint, so any division is ignored.
        (28800, "2020-11-16", 28700, "x", {"x": (0, True)}, 0),
        (28800, "2020-11-16", 28700, "x", {"x": (0.6, True)}, 0),
        # b. Negative timezone.
        # ---------------------
        # It can span two sprints.
        (28800, "2020-11-16", 28700, "x", {"x": (0.4, False)}, 60),
        # Otherwise treat is as a part of the current sprint.
        (28800, "2020-11-16", 28700, "x", {"x": (0, False)}, 0),
        # 2. First day of the next sprint.
        # ================================
        # a. Positive timezone.
        # ---------------------
        # It can span two sprints.
        (28800, "2020-11-17", 28700, "x", {"x": (0.6, True)}, 40),
        # Otherwise treat is as a part of the current sprint.
        (28800, "2020-11-17", 28700, "x", {"x": (0, True)}, 100),
        # b. Negative timezone.
        # ---------------------
        # It can be only in the next sprint.
        (28800, "2020-11-17", 28700, "x", {"x": (0, False)}, 100),
        (28800, "2020-11-17", 28700, "x", {"x": (0.4, False)}, 100),
        # 3. Last day of the next sprint.
        # ===============================
        # a. Positive timezone.
        # ---------------------
        # It can be only in the next sprint.
        (28800, "2020-11-30", 28700, "x", {"x": (0, True)}, 100),
        (28800, "2020-11-30", 28700, "x", {"x": (0.6, True)}, 100),
        # b. Negative timezone.
        # ---------------------
        # It can span two sprints.
        (28800, "2020-11-30", 28700, "x", {"x": (0.4, False)}, 40),
        # Otherwise treat is as a part of the next sprint.
        (28800, "2020-11-30", 28700, "x", {"x": (0, False)}, 100),
        # 4. Day after the end of the sprint.
        # ===================================
        # a. Positive timezone.
        # ---------------------
        # It can span two sprints.
        (28800, "2020-12-1", 28700, "x", {"x": (0.6, True)}, 60),
        # Otherwise treat is as a part of the future next sprint.
        (28800, "2020-12-1", 28700, "x", {"x": (0, True)}, 0),
        # b. Negative timezone.
        # ---------------------
        # It can be only in the future next sprint.
        (28800, "2020-12-1", 28700, "x", {"x": (0, False)}, 0),
        (28800, "2020-12-1", 28700, "x", {"x": (0.4, False)}, 0),
        # 5. Standard cases.
        # ==================
        # Vacations scheduled in the middle of the sprint.
        (28800, "2020-11-20", 28700, "x", {"x": (0, False)}, 100),
        (28800, "2020-11-20", 28700, "x", {"x": (0.4, False)}, 100),
        (28800, "2020-11-20", 28700, "x", {"x": (0, True)}, 100),
        (28800, "2020-11-20", 28700, "x", {"x": (0.4, True)}, 100),
    ],
)
def test_get_vacation_for_day(
    commitments, date, planned_commitments, username, division, expected
):
    mock_dashboard = object.__new__(Dashboard)
    mock_dashboard.future_sprint_start = "2020-11-17"
    mock_dashboard.future_sprint_end = "2020-11-30"
    mock_dashboard.sprint_division = division

    assert (
        mock_dashboard._get_vacation_for_day(
            commitments, date, planned_commitments, username
        )
        == expected
    )
