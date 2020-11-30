from typing import List

from django.conf import settings
from mattermostdriver import Driver
from requests import HTTPError


class Mattermost:
    """Class that is responsible for connecting to mattermost bot."""

    def __init__(self):
        """
        :param username: Username of the mattermost bot.
        :param access_token: Access token for the bot.
        """
        connection_parameters = {
            'url': settings.MATTERMOST_SERVER,
            'port': settings.MATTERMOST_PORT,
            'username': settings.MATTERMOST_LOGIN_ID,
            'token': settings.MATTERMOST_ACCESS_TOKEN
        }
        self.mattermost_connection = Driver(connection_parameters)

    def __enter__(self):
        try:
            self.mattermost_connection.login()
        except HTTPError as e:
            # noinspection PyUnresolvedReferences
            from sentry_sdk import capture_exception
            capture_exception(e)
        return self

    def __exit__(self, *args):
        self.mattermost_connection.logout()

    def get_usernames_from_emails(self, emails: List[str]) -> List[str]:
        """
        Function that helps to get mattermost usrenames
        from emails.

        :param emails: Emails of the users.
        :return: Mattermost usernames of the users.
        """
        usernames = []
        for email in emails:
            try:
                username = self.mattermost_connection.users.get_user_by_email(email=email).get('username')
                if username:
                    usernames.append(username)
            except HTTPError as e:
                # noinspection PyUnresolvedReferences
                from sentry_sdk import capture_exception
                capture_exception(e)

        return usernames

    def post_message_to_channel(self, channel_name: str, message: str) -> None:
        """
        Post the message to the channel using the channel name.

        :param channel_name: Name of the channel to post message.
        :param message: Message to be posted.
        """
        try:
            channels = self.mattermost_connection.channels
            channel_id = channels.get_channel_by_name_and_team_name(
                settings.MATTERMOST_TEAM_NAME, channel_name).get('id')
            self.mattermost_connection.posts.create_post({'channel_id': channel_id, 'message': message})
        except HTTPError as e:
            # noinspection PyUnresolvedReferences
            from sentry_sdk import capture_exception
            capture_exception(e)


def create_mattermost_post(message: str, emails: List[str]) -> None:
    """
    Function that helps to create post in specific channel tagging the users
    in them.

    :param message: The message to be posted in mattermost.
    :param emails: Email ids of the users.
    """
    with Mattermost() as conn:
        tagged_usernames = [f'@{username}'
                            for username in conn.get_usernames_from_emails(emails)]
        if tagged_usernames:
            usernames = ', '.join(tagged_usernames)
            post = f'{usernames} : {message}'
            conn.post_message_to_channel(settings.MATTERMOST_CHANNEL, post)
