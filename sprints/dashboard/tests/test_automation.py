from datetime import (
    datetime,
    timedelta,
)
from unittest.mock import (
    Mock,
    patch,
)

import pytest
from dateutil.parser import parse
from django.conf import settings
from django.test import override_settings
from freezegun import freeze_time

from dashboard.tests.test_utils import MockItem
from sprints.dashboard.automation import (
    check_issue_injected,
    check_issue_missing_fields,
    flag_issue,
    get_current_sprint_day,
    get_next_sprint_issues,
    get_overcommitted_users,
    get_specific_day_of_sprint,
    get_users_to_ping,
    group_incomplete_issues,
    notify_about_injection,
    unflag_issue,
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
def test_get_current_sprint_day(get_sprint_start_date: Mock, test_date: str, expected: int):
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
def test_get_specific_day_of_sprint(get_sprint_start_date: Mock, day: int, expected_date: datetime):
    get_sprint_start_date.return_value = "2020-10-20"
    assert get_specific_day_of_sprint(day) == expected_date


@patch("sprints.dashboard.automation.get_issue_fields")
@patch("sprints.dashboard.automation.get_all_sprints")
@pytest.mark.parametrize("changelog, expected_expand", [(False, ""), (True, "changelog")])
def test_get_next_sprint_issues(get_all_sprints: Mock, get_issue_fields: Mock, changelog: bool, expected_expand: str):
    get_all_sprints.return_value = {
        'future': [
            Mock(id=123),
            Mock(id=124),
        ]
    }
    get_issue_fields.return_value = {'test_field': 'testfield'}
    mock_jira = Mock()
    mock_jira.search_issues = Mock()

    get_next_sprint_issues(mock_jira, changelog)

    mock_jira.search_issues.assert_called_once_with(
        jql_str='Sprint IN (123,124)',
        fields=['testfield'],
        expand=expected_expand,
        maxResults=0,
    )


ASSIGNEE = "Assignee"
EPIC_OWNER = "Epic Owner"
EPIC = "Epic"
REPORTER = "Reporter"


@override_settings(DEBUG=True)  # `sentry_sdk` does not capture exceptions in `DEBUG` mode.
@pytest.mark.parametrize(
    "assignee, epic_owner, reporter, epic_link, include_epic, expected",
    [
        (None, EPIC_OWNER, None, None, False, set()),
        (None, EPIC_OWNER, REPORTER, EPIC, False, {EPIC_OWNER}),
        (None, None, REPORTER, EPIC, False, {REPORTER}),
        (ASSIGNEE, None, None, None, False, {ASSIGNEE}),
        (ASSIGNEE, EPIC_OWNER, REPORTER, EPIC, False, {ASSIGNEE}),
        (ASSIGNEE, EPIC_OWNER, REPORTER, EPIC, True, {ASSIGNEE, EPIC_OWNER}),
    ],
)
def test_get_users_to_ping(
    assignee: str, epic_owner: str, reporter: str, epic_link: str, include_epic: bool, expected: set[str]
):
    mock_jira = Mock()
    mock_jira.issue_fields = {
        settings.JIRA_FIELDS_ASSIGNEE: 'assignee',
        settings.JIRA_FIELDS_EPIC_LINK: 'epic_link',
        settings.JIRA_FIELDS_REPORTER: 'reporter',
    }
    mock_epic = Mock()
    setattr(mock_epic.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_ASSIGNEE], epic_owner)
    mock_jira.issue.return_value = mock_epic

    mock_issue = Mock()
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_ASSIGNEE], assignee)
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_REPORTER], reporter)
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_EPIC_LINK], epic_link)

    assert get_users_to_ping(mock_jira, mock_issue, include_epic) == expected


@override_settings(SPRINT_ASYNC_INJECTION_MESSAGE="issue moved to ")
@patch("sprints.dashboard.automation.get_users_to_ping")
@pytest.mark.parametrize(
    "users, expected_message",
    [
        (set(), f"issue moved to another_sprint."),
        ({MockItem(name="User1")}, "[~User1], issue moved to another_sprint."),
        ([MockItem(name="User1"), MockItem(name="User2")], "[~User1], [~User2], issue moved to another_sprint."),
    ],
)
def test_notify_about_injection(mock_get_users_to_ping: Mock, users: set[Mock], expected_message: str):
    mock_jira = Mock()
    mock_sprint = MockItem(id=123, name="another_sprint")
    mock_issue = Mock(key="T1-111")
    mock_get_users_to_ping.return_value = users

    # noinspection PyTypeChecker
    notify_about_injection(mock_jira, mock_issue, mock_sprint)
    mock_jira.add_comment.assert_called_once_with(mock_issue.key, expected_message)


@patch("sprints.dashboard.automation.check_issue_missing_fields")
@patch("sprints.dashboard.automation.get_users_to_ping")
@pytest.mark.parametrize(
    "issues, missing_fields, users_to_ping, expected",
    [
        ([], [[]], [[]], {}),
        ([Mock(key='T1-1')], [[]], [["User1"]], {}),
        ([Mock(key='T1-1')], [["Reviewer"]], [[]], {}),
        (
            [Mock(key='T1-1'), Mock(key='T1-2'), Mock(key='T1-3')],
            [["Reviewer"], ["Assignee", "Story Points"], []],
            [["User1"], ["User1", "User2"], ["User2"]],
            {
                "User1": {
                    "T1-1": [
                        "Reviewer",
                    ],
                    "T1-2": [
                        "Assignee",
                        "Story Points",
                    ],
                },
                "User2": {
                    "T1-2": [
                        "Assignee",
                        "Story Points",
                    ]
                },
            },
        ),
    ],
)
def test_group_incomplete_issues(
    mock_get_users_to_ping: Mock,
    mock_check_issue_missing_fields: Mock,
    issues: list[Mock],
    missing_fields: list[str],
    users_to_ping: list[str],
    expected: dict[str, dict[str, list[str]]],
):
    mock_check_issue_missing_fields.side_effect = missing_fields
    mock_get_users_to_ping.side_effect = users_to_ping

    result = group_incomplete_issues(Mock(), issues)
    for user, issues in expected.items():
        for issue, fields in issues.items():
            # noinspection PyTypeChecker
            assert result[user][issue] == fields


FLAG = [{"value": "Impediment"}]


@pytest.mark.parametrize("current_flag, should_invoke", [(FLAG, False), (None, True)])
def test_flag_issue(current_flag: list[dict[str, str]], should_invoke: bool):
    mock_jira = Mock()
    mock_jira.issue_fields = {settings.JIRA_FIELDS_FLAGGED: "flagged"}

    mock_issue = Mock()
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_FLAGGED], current_flag)

    flag_issue(mock_jira, mock_issue)

    if not should_invoke:
        mock_issue.update.assert_not_called()
    else:
        mock_issue.update.assert_called_once_with(fields={mock_jira.issue_fields[settings.JIRA_FIELDS_FLAGGED]: FLAG})


@pytest.mark.parametrize("current_flag, should_invoke", [(None, False), (FLAG, True)])
def test_unflag_issue(current_flag: list[dict[str, str]], should_invoke: bool):
    mock_jira = Mock()
    mock_jira.issue_fields = {settings.JIRA_FIELDS_FLAGGED: "flagged"}

    mock_issue = Mock()
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_FLAGGED], current_flag)

    unflag_issue(mock_jira, mock_issue)

    if not should_invoke:
        mock_issue.update.assert_not_called()
    else:
        mock_issue.update.assert_called_once_with(fields={mock_jira.issue_fields[settings.JIRA_FIELDS_FLAGGED]: None})


@patch("sprints.dashboard.automation.get_specific_day_of_sprint", return_value=parse("2020-10-20"))
@pytest.mark.parametrize(
    "changed_date, labels, expected",
    [
        ("2020-10-19T23:59:59", [], False),
        ("2020-10-20T00:00:00", [], True),
        ("2020-10-20T00:00:00", [settings.SPRINT_ASYNC_INJECTION_LABEL], False),
    ],
)
def test_check_issue_injected(_mock: Mock, changed_date: str, labels: list[str], expected: bool):
    mock_jira = Mock()
    mock_jira.issue_fields = {settings.JIRA_FIELDS_LABELS: "labels"}

    mock_issue = Mock()
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_LABELS], labels)
    mock_issue.changelog.histories = [
        Mock(
            created=(parse(changed_date) - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            items=[Mock(field="Sprint")],
        ),
        Mock(created=changed_date, items=[Mock(field="Sprint")]),
        Mock(
            created=(parse(changed_date) + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S"),
            items=[Mock(field="timeoriginalestimate"), Mock(field="timeestimate")],
        ),
    ]

    assert check_issue_injected(mock_jira, mock_issue) is expected


@pytest.mark.parametrize(
    "assignee, reviewer, story_points, expected",
    [
        (
            None,
            None,
            None,
            [settings.JIRA_FIELDS_ASSIGNEE, settings.JIRA_FIELDS_REVIEWER, settings.JIRA_FIELDS_STORY_POINTS],
        ),
        ("User1", None, None, [settings.JIRA_FIELDS_REVIEWER, settings.JIRA_FIELDS_STORY_POINTS]),
        ("User1", "User2", None, [settings.JIRA_FIELDS_STORY_POINTS]),
        ("User1", "User2", 1, []),
    ],
)
def test_check_issue_missing_fields(assignee: str, reviewer: str, story_points: int, expected: list[str]):
    mock_jira = Mock()
    mock_jira.issue_fields = {
        settings.JIRA_FIELDS_ASSIGNEE: 'assignee',
        settings.JIRA_FIELDS_REVIEWER: 'reviewer',
        settings.JIRA_FIELDS_STORY_POINTS: 'story_points',
    }

    mock_issue = Mock()
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_ASSIGNEE], assignee)
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_REVIEWER], reviewer)
    setattr(mock_issue.fields, mock_jira.issue_fields[settings.JIRA_FIELDS_STORY_POINTS], story_points)

    assert check_issue_missing_fields(mock_jira, mock_issue) == expected


USER_1 = Mock(name="User1")
USER_2 = Mock(name="User2")
USER_3 = Mock(name="User3")
USER_4 = Mock(name="User4", raw="test_data")
USER_5 = Mock(name="User5", raw=None)  # Special case - artificial user (like "Unassigned").


@patch("sprints.dashboard.automation.Dashboard")
@patch("sprints.dashboard.automation.get_cells")
@pytest.mark.parametrize(
    "cells, dashboards, expected",
    [
        ([], [], {}),
        (
            [MockItem(name="T1", board_id=1), MockItem(name="T2", board_id=2), MockItem(name="T3", board_id=2)],
            [
                Mock(
                    cell=MockItem(name="T1"),
                    rows=[
                        Mock(remaining_time=0, user=USER_1),
                        Mock(remaining_time=-1, user=USER_2),
                        Mock(remaining_time=-10, user=USER_3),
                    ],
                ),
                Mock(
                    cell=MockItem(name="T2"),
                    rows=[
                        Mock(remaining_time=-2, user=USER_4),
                    ],
                ),
                Mock(
                    cell=MockItem(name="T3"),
                    rows=[
                        Mock(remaining_time=-2, user=USER_5),
                    ],
                ),
            ],
            {"T1": [USER_2, USER_3], "T2": [USER_4]},
        ),
    ],
)
def test_get_overcommitted_users(
    mock_get_cells: Mock, mock_dashboard: Mock, cells: list[MockItem], dashboards: list[Mock], expected: list[str]
):
    mock_jira = Mock()
    mock_get_cells.return_value = cells

    mock_dashboard.side_effect = dashboards

    assert get_overcommitted_users(mock_jira) == expected
