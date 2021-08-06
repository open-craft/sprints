import pytest
from unittest.mock import (
    Mock,
    patch
)


from django.conf import settings
from django.test import override_settings

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
def test_get_vacation_for_day(commitments, date, planned_commitments, username, division, expected):
    mock_dashboard = object.__new__(Dashboard)
    mock_dashboard.future_sprint_start = "2020-11-17"
    mock_dashboard.future_sprint_end = "2020-11-30"
    mock_dashboard.sprint_division = division

    assert mock_dashboard._get_vacation_for_day(commitments, date, planned_commitments, username) == expected


@pytest.mark.parametrize(
    "story_points, expected_hours",
    [
        # story points not defined
        (None, 2),
        # less than 1.9 story points
        (0.5, 0.5),
        (1.77, 0.5),
        (1, 0.5),
        # 2 and near to 2 story points
        (1.99, 1),
        (2, 1),
        (2.3, 1),
        (2.5, 1),
        # 3 and near to 3 story points
        (2.6, 2),
        (3, 2),
        (3.3, 2),
        # 5 and near to 5 story points
        (4.6, 3),
        (5, 3),
        (5.01, 3),
        # more than 5.1 story points
        (5.2, 5),
        (10, 5),
    ],
)
@override_settings(
    SPRINT_HOURS_RESERVED_FOR_REVIEW={
        None: 2,
        1.9: 0.5,
        2: 1,
        3: 2,
        5: 3,
        5.1: 5
    }
)
def test_calculate_review_time_from_story_points(story_points, expected_hours):
    mock_issue = object.__new__(DashboardIssue)
    mock_issue.story_points = story_points
    assert mock_issue.calculate_review_time_from_story_points() == expected_hours


@patch.object(DashboardIssue, "get_bot_directive")
def test_review_time_bot_directives_given(mock_get_bot_directives):
    time_specified_by_bot_directive = 3
    mock_get_bot_directives.return_value = time_specified_by_bot_directive
    mock_dashboard = object.__new__(DashboardIssue)

    assert mock_dashboard.review_time == time_specified_by_bot_directive


@patch.object(DashboardIssue, "get_bot_directive")
def test_review_time_no_bot_directive_and_is_epic(mock_get_bot_directives):
    review_time_if_issue_is_epic = 0
    mock_get_bot_directives.side_effect = ValueError
    mock_dashboard = object.__new__(DashboardIssue)
    mock_dashboard.is_epic = True

    assert mock_dashboard.review_time == review_time_if_issue_is_epic


@pytest.mark.parametrize(
    "status",
    [status for status in settings.SPRINT_STATUS_NO_MORE_REVIEW]
)
@patch.object(DashboardIssue, "get_bot_directive")
def test_review_time_no_bot_directive_and_does_not_need_a_review(mock_get_bot_directive, status):
    review_time_if_issue_does_not_need_review = 0
    mock_get_bot_directive.side_effect = ValueError
    mock_dashboard = object.__new__(DashboardIssue)
    mock_dashboard.status = status
    mock_dashboard.is_epic = False

    assert mock_dashboard.review_time == review_time_if_issue_does_not_need_review


@patch.object(DashboardIssue, "get_bot_directive")
@patch.object(DashboardIssue, "calculate_review_time_from_story_points")
def test_review_time_no_bot_directive_given(mock_get_bot_directive, mock_review_time_from_story_points):
    expected_review_time = 3
    mock_get_bot_directive.side_effect = ValueError
    mock_review_time_from_story_points.return_value = expected_review_time
    mock_dashboard = object.__new__(DashboardIssue)
    mock_dashboard.is_epic = False

    assert mock_dashboard.review_time == expected_review_time
