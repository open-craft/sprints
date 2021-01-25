import re
from unittest import TestCase
from unittest.mock import patch, Mock

import pytest
from django.conf import settings
from django.test import override_settings

from sprints.dashboard.tests.helpers import does_not_raise
from sprints.dashboard.utils import (
    NoRolesFoundException,
    _column_number_to_excel,
    _get_sprint_meeting_day_division_for_member,
    extract_sprint_id_from_str,
    extract_sprint_name_from_str,
    extract_sprint_start_date_from_sprint_name,
    get_all_sprints,
    get_cell_key,
    get_cell_members,
    get_cells,
    get_issue_fields,
    get_next_sprint,
    get_projects_dict,
    get_sprint_number,
    prepare_jql_query,
    prepare_jql_query_active_sprint_tickets,
    prepare_spillover_rows,
    get_cell_member_roles,
    get_rotations_roles_for_member,
    compile_participants_roles,
)


class MockItem:
    def __init__(self, **kwargs) -> None:
        super().__init__()
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._attrs = kwargs.keys()

    def __eq__(self, other):
        for attr in self._attrs:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __repr__(self):
        return ', '.join([getattr(self, attr) for attr in self._attrs])


class MockJiraConnection:
    @staticmethod
    def boards(name=''):
        boards = [
            MockItem(id=1, name=f'{settings.JIRA_SPRINT_BOARD_PREFIX}Test1'),
            MockItem(id=2, name=f'{settings.JIRA_SPRINT_BOARD_PREFIX}Test2'),
            MockItem(id=3, name=f'Test3'),
        ]
        if name:
            # noinspection PyUnresolvedReferences
            return [board for board in boards if board.name.startswith(settings.JIRA_SPRINT_BOARD_PREFIX)]
        return boards

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

    @staticmethod
    def sprints(board_id, **_kwargs):
        if board_id == 1:
            return [
                MockItem(name='T1.125 (2019-01-01)', state='future'),
                MockItem(name='T1.123 (2019-01-01)', state='active'),
            ]
        return [
            MockItem(name='T2.124 (2019-01-01)', state='future'),
            MockItem(name='T1.124 (2019-01-01)', state='future'),
        ]

    @staticmethod
    def projects():
        return [
            MockItem(name='Test1', key='T1'),
            MockItem(name='Test2', key='T2'),
            MockItem(name='Test3', key='T3'),
        ]


def test_get_projects_dict():
    # noinspection PyTypeChecker
    projects = get_projects_dict(MockJiraConnection())
    expected = {
        'Test1': MockItem(name='Test1', key='T1'),
        'Test2': MockItem(name='Test2', key='T2'),
        'Test3': MockItem(name='Test3', key='T3'),
    }
    assert projects == expected


def test_get_cells():
    # noinspection PyTypeChecker
    cells = get_cells(MockJiraConnection())
    assert len(cells) == 2
    assert cells[0].name == 'Test1'
    assert cells[0].board_id == 1
    assert cells[0].key == 'T1'
    assert cells[1].name == 'Test2'
    assert cells[1].board_id == 2
    assert cells[1].key == 'T2'


@pytest.mark.parametrize(
    "test_input, expected, raises", [
        (1, 'T1', does_not_raise()),
        (2, 'T2', does_not_raise()),
        (3, 'T3', pytest.raises(ValueError)),
    ],
)
def test_get_cell_key(test_input, expected, raises):
    with raises:
        # noinspection PyTypeChecker
        assert get_cell_key(MockJiraConnection(), test_input) == expected


def test_get_cell_members():
    quickfilters = [
        MockItem(query='assignee = Test1 or reviewer_1 = Test1 or reviewer_2 = Test1'),
        MockItem(query='assignee = Test2'),
        MockItem(query='Test3'),
    ]
    # noinspection PyTypeChecker
    members = get_cell_members(quickfilters)
    assert len(members) == 1
    assert members[0] == 'Test1'


def test_get_sprint_number():
    sprint = MockItem(name='T1.123 (2019-01-01)', state='active')
    # noinspection PyTypeChecker
    assert get_sprint_number(sprint) == 123


def test_get_next_sprint():
    sprints = [
        MockItem(name='T1.125 (2019-01-01)', state='future'),
        MockItem(name='T1.123 (2019-01-01)', state='active'),
        MockItem(name='T1.124 (2019-01-01)', state='future'),
    ]
    # noinspection PyTypeChecker
    assert get_next_sprint(sprints, sprints[1]) == sprints[2]

    # noinspection PyTypeChecker
    assert get_next_sprint(sprints, sprints[2]) == sprints[0]

    # noinspection PyTypeChecker
    assert get_next_sprint(sprints, sprints[0]) is None  # Next sprint not found


def test_get_all_sprints():
    # noinspection PyTypeChecker
    sprints = get_all_sprints(MockJiraConnection())
    expected = {
        'active': [
            MockItem(name='T1.123 (2019-01-01)', state='active'),
        ],
        'future': [
            MockItem(name='T2.124 (2019-01-01)', state='future'),
            MockItem(name='T1.124 (2019-01-01)', state='future'),
        ],
        'all': [
            MockItem(name='T1.125 (2019-01-01)', state='future'),
            MockItem(name='T1.123 (2019-01-01)', state='active'),
            MockItem(name='T2.124 (2019-01-01)', state='future'),
            MockItem(name='T1.124 (2019-01-01)', state='future'),
        ]
    }
    assert sprints == expected


def test_prepare_jql_query():
    expected_fields = ['id', 'sprint']
    expected_result = {
        'jql_str': r'^\(Sprint IN \(245,246\) AND status IN \(.*?\) OR \(issuetype = Epic AND Status IN \(.*?\)\)$',
        'fields': expected_fields,
    }
    result = prepare_jql_query(
        sprints=['245', '246'],
        fields=expected_fields,
    )
    assert result['fields'] == expected_result['fields']
    assert re.match(expected_result['jql_str'], result['jql_str'])


def test_extract_sprint_id_from_str():
    sprint_str = 'com.atlassian.greenhopper.service.sprint.Sprint@614e3007[id=245,rapidViewId=26,state=CLOSED,' \
                 'name=Sprint 197 (2019-06-18),startDate=2019-06-17T17:21:26.945Z,' \
                 'endDate=2019-07-01T17:21:00.000Z,completeDate=2019-07-01T17:46:48.977Z,sequence=243,goal=] '
    assert extract_sprint_id_from_str(sprint_str) == 245


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


@pytest.mark.parametrize(
    "test_input, expected, raises", [
        ('Sprint 201 (2019-08-13)', '2019-08-13', does_not_raise()),
        ('SE.202 (2019-08-27)', '2019-08-27', does_not_raise()),
        ('Sprint 201 (2019-08-13', '', pytest.raises(AttributeError)),
    ],
)
def test_extract_sprint_start_date_from_sprint_name(test_input, expected, raises):
    with raises:
        assert extract_sprint_start_date_from_sprint_name(test_input) == expected


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


@pytest.mark.parametrize(
    "test_input, expected", [
        ('name=Sprint 197 (2019-06-18),startDate=2019-06-17T17:21:26.945Z', 'Sprint 197 (2019-06-18)'),
        ('name=TS.197 (2019-06-18),startDate=2019-06-17T17:21:26.945Z', 'TS.197 (2019-06-18)'),
    ],
)
def test_extract_sprint_name_from_str(test_input, expected):
    assert extract_sprint_name_from_str(test_input) == expected


def test_get_issue_fields():
    required_fields = ('example_name1', 'example_name2')
    expected_result = {
        required_fields[0]: 'example_id1',
        required_fields[1]: 'example_id2',
    }
    # noinspection PyTypeChecker
    assert get_issue_fields(MockJiraConnection(), required_fields) == expected_result


@override_settings(JIRA_SERVER='https://example.com', SPILLOVER_REQUIRED_FIELDS=('Story Points', 'Original Estimate'))
def test_prepare_spillover_rows():
    test_issues = [
        MockItem(
            key='TEST-1',
            fields=MockItem(story_points=1., original_estimate=7200)
        ),
        MockItem(
            key='TEST-2',
            fields=MockItem(story_points=3.14, original_estimate=9849)  # estimated time should be rounded up here
        ),
    ]
    issue_fields = {
        'Story Points': 'story_points',
        'Original Estimate': 'original_estimate',
    }
    expected_result = [
        ['=HYPERLINK("https://example.com/browse/TEST-1","TEST-1")', '1', '2.0'],
        ['=HYPERLINK("https://example.com/browse/TEST-2","TEST-2")', '3', '2.74'],
    ]
    # noinspection PyTypeChecker
    assert prepare_spillover_rows(test_issues, issue_fields, {}) == expected_result


@pytest.mark.parametrize(
    "test_input, expected", [
        (1, 'A'),
        (26, 'Z'),
        (27, 'AA'),
        (52, 'AZ'),
        (53, 'BA'),
        (702, 'ZZ'),
        (703, 'AAA'),
        (18278, 'ZZZ'),
        (18279, 'AAAA'),
        (214570915, 'RANDOM'),
    ],
)
def test_column_number_to_excel(test_input, expected):
    assert _column_number_to_excel(test_input) == expected


@override_settings(DEBUG=True)  # `sentry_sdk` does not capture exceptions in `DEBUG` mode.
@pytest.mark.parametrize(
    "hours, expected",
    [
        ("12pm-9pm*", 0),
        ("3pm-12am", 0),
        ("12am-2am", 0),
        ("3pm - 1am", 0.9),
        ("11:30pm-2am", 0.2),
        ("invalid", 0),
    ],
)
def test_get_sprint_meeting_day_division_for_member(hours, expected):
    sprint_start = "2020-01-01"
    assert _get_sprint_meeting_day_division_for_member(hours, sprint_start) == pytest.approx(expected, 0.1)

@patch("requests.get")
def test_get_cell_member_roles(mock_get):
    with open("sprints/dashboard/tests/data/handbook/dummy_cells.html", 'r') as f:
        mock_get.return_value = Mock(text=f.read())
        output = dict(get_cell_member_roles())
        expected_output = {
                            "Member Six": ["Recruitment manager"],
                            "Member Seven": ["Sprint manager"],
                            "Member Five": ["Sprint Planning Manager"],
                            "Member Eight": ["Epic manager"],
                            "Member Two": ["Sustainability manager"],
                            "Member Four": ["OSPR Liaison", "Official forum moderator"],
                            "Member One": ["DevOps Specialist"],
                        }
        TestCase().assertDictEqual(output, expected_output)

@patch("requests.get")
def test_get_cell_member_roles_corrupted(mock_get):
    with open("sprints/dashboard/tests/data/handbook/dummy_cells_corrupted.html", 'r') as f:
        mock_get.return_value = Mock(text=f.read())
        with TestCase().assertRaises(NoRolesFoundException):
            get_cell_member_roles()

def test_get_rotations_roles_for_member():
    # When the member is on FF duty
    output = get_rotations_roles_for_member('John Doe', {'FF': ['Jake Doe', 'John Doe'], 'DD': ['Jane Doe', 'James Doe']})
    assert len(output) == 1
    assert output[0] == 'FF-2'

    # When member has no duty
    output = get_rotations_roles_for_member('John Doe', {'FF': ['Jake Doe', 'James Doe'], 'DD': ['Jane Doe', 'James Doe']})
    assert len(output) == 0

    # When only partial name of the member is defined
    output = get_rotations_roles_for_member('John Doe', {'FF': ['John Doe', 'Jake Doe'], 'DD': ['Jane Doe', 'James Doe']})
    assert len(output) == 1
    assert output[0] == 'FF-1'

def test_compile_participants_roles():
    members_data_dummy = [
        Mock(displayName='Jane Doe', emailAddress='janedoe@opencraft.com'),
        Mock(displayName='Jack Doe', emailAddress='jackdoe@opencraft.com'),
        Mock(displayName='John Doe', emailAddress='johndoe@opencraft.com'),
        Mock(displayName='Jake Doe', emailAddress='jakedoe@opencraft.com'),
    ]

    rotations_data_dummy = {
        'ff': ['John Doe', 'Jack'],
        'dd': ['Jack Doe', 'Jake Doe'],
    }

    roles_data_dummy = {
        'Jane Doe': [],
        'Jack Doe': ['Sprint Planning Manager', 'DevOps Specialist'],
        'John Doe': ['Sprint Manager'],
        'Jake Doe': ['Recruitment Manager'],
        'Juan Doe': [''],
    }

    output = compile_participants_roles(members_data_dummy, rotations_data_dummy, roles_data_dummy)

    expected_output = {
        'janedoe@opencraft.com': [],
        'jackdoe@opencraft.com': ['Sprint Planning Manager', 'DevOps Specialist', 'ff-2', 'dd-1'],
        'johndoe@opencraft.com': ['Sprint Manager', 'ff-1'],
        'jakedoe@opencraft.com': ['Recruitment Manager', 'dd-2']
    }

    TestCase().assertDictEqual(output, expected_output)
