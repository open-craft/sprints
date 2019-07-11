import pytest
from django.test import override_settings

from sprints.dashboard.utils import (
    extract_sprint_name_from_str,
    get_issue_fields,
    prepare_jql_query_active_sprint_tickets,
    prepare_spillover_rows,
)

pytestmark = pytest.mark.django_db


class MockIssue:
    class MockIssueFields:
        def __init__(self, **kwargs) -> None:
            super().__init__()
            for k, v in kwargs.items():
                setattr(self, k, v)

    def __init__(self, key, **kwargs) -> None:
        super().__init__()
        self.key = key
        self.fields = self.MockIssueFields(**kwargs)


class MockJiraConnection:
    @staticmethod
    def fields():
        return [
            {
                'name': 'example_name1',
                'id': 'example_id1',
            },
            {
                'name': 'example_name2',
                'id': 'example_id2',
            },
            {
                'name': 'example_name3',
                'id': 'example_id3',
            },
        ]


def test_prepare_jql_query_active_sprint_tickets():
    expected_fields = ['id']
    expected_result = {
        'jql_str': 'Sprint IN openSprints() AND status IN ("Backlog","In progress","Need Review","Merged")',
        'fields': expected_fields,
    }
    result = prepare_jql_query_active_sprint_tickets(
        expected_fields,
        ("Backlog", "In progress", "Need Review", "Merged"),
    )
    assert result == expected_result


def test_prepare_jql_query_active_sprint_tickets_for_project():
    expected_fields = ['id']
    expected_result = {
        'jql_str': 'project = TEST AND Sprint IN openSprints() AND status IN ("Backlog","In progress")',
        'fields': expected_fields,
    }
    result = prepare_jql_query_active_sprint_tickets(
        expected_fields,
        ("Backlog", "In progress"),
        project="TEST",
    )
    assert result == expected_result


def test_extract_sprint_name_from_str():
    sprint_str = 'com.atlassian.greenhopper.service.sprint.Sprint@614e3007[id=245,rapidViewId=26,state=CLOSED,' \
                 'name=Sprint 197 (2019-06-18),startDate=2019-06-17T17:21:26.945Z,' \
                 'endDate=2019-07-01T17:21:00.000Z,completeDate=2019-07-01T17:46:48.977Z,sequence=243,goal=] '
    assert extract_sprint_name_from_str(sprint_str) == 'Sprint 197 (2019-06-18)'


def test_get_issue_fields():
    required_fields = ('example_name1', 'example_name2')
    expected_result = {
        required_fields[0]: 'example_id1',
        required_fields[1]: 'example_id2',
    }
    assert get_issue_fields(MockJiraConnection(), required_fields) == expected_result


@override_settings(JIRA_SERVER='https://example.com', SPILLOVER_REQUIRED_FIELDS=('Story Points', 'Original Estimate'))
def test_prepare_spillover_rows():
    test_issues = [
        MockIssue('TEST-1', story_points=1., original_estimate=7200),
        MockIssue('TEST-2', story_points=3.14, original_estimate=9849),  # estimated time should be rounded up here
    ]
    issue_fields = {
        'Story Points': 'story_points',
        'Original Estimate': 'original_estimate',
    }
    expected_result = [
        ['=HYPERLINK("https://example.com/browse/TEST-1","TEST-1")', '1', '2.0'],
        ['=HYPERLINK("https://example.com/browse/TEST-2","TEST-2")', '3', '2.74'],
    ]
    assert prepare_spillover_rows(test_issues, issue_fields) == expected_result
