from unittest.mock import patch

from django.test import override_settings

from sprints.dashboard.libs.mattermost import create_mattermost_post


def side_effect_usernames_from_emails(emails):
    usernames = []
    username_email_map = {'farhaan@example.com': 'farhaan',
                          'piotr@example.com': 'piotr', 'demid@example.com': 'demid'}
    for email in emails:
        username = username_email_map.get(email)
        if username:
            usernames.append(username)
    return usernames


@override_settings(MATTERMOST_CHANNEL='test_channel')
@patch('sprints.dashboard.libs.mattermost.Mattermost')
def test_message_format(mock_mattermost):
    get_usernames_from_emails_mock = mock_mattermost.return_value.__enter__.return_value.get_usernames_from_emails
    get_usernames_from_emails_mock.side_effect = side_effect_usernames_from_emails
    post_message_to_channel_mock = mock_mattermost.return_value.__enter__.return_value.post_message_to_channel
    create_mattermost_post('Hello, World!', ['farhaan@example.com', 'piotr@example.com', 'demid@example.com'])
    post_message_to_channel_mock.assert_called_with('test_channel', '@farhaan, @piotr, @demid : Hello, World!')


@override_settings(MATTERMOST_CHANNEL='test_channel')
@patch('sprints.dashboard.libs.mattermost.Mattermost')
def test_with_no_username(mock_mattermost):
    get_usernames_from_emails_mock = mock_mattermost.return_value.__enter__.return_value.get_usernames_from_emails
    get_usernames_from_emails_mock.side_effect = side_effect_usernames_from_emails
    post_message_to_channel_mock = mock_mattermost.return_value.__enter__.return_value.post_message_to_channel
    create_mattermost_post('Hello, World!', ['nousername@example.com', 'piotr@example.com', 'demid@example.com'])
    post_message_to_channel_mock.assert_called_with('test_channel', '@piotr, @demid : Hello, World!')


@override_settings(MATTERMOST_CHANNEL='test_channel')
@patch('sprints.dashboard.libs.mattermost.Mattermost')
def test_with_all_username_missing(mock_mattermost):
    get_usernames_from_emails_mock = mock_mattermost.return_value.__enter__.return_value.get_usernames_from_emails
    get_usernames_from_emails_mock.side_effect = side_effect_usernames_from_emails
    post_message_to_channel_mock = mock_mattermost.return_value.__enter__.return_value.post_message_to_channel
    create_mattermost_post('Hello, World!', ['nousername@example.com', 'nouse1@example.com', 'nouse2@example.com'])
    assert get_usernames_from_emails_mock.called
    assert not post_message_to_channel_mock.called
