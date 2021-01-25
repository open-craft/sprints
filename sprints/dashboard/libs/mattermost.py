from django.conf import settings
from mattermostdriver import Driver
from requests import HTTPError


class Mattermost:
    """Class that is responsible for connecting to mattermost bot."""

    def __init__(self):
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
            # Log exception to Sentry if call fails, but do not break the server.
            if not settings.DEBUG:
                # noinspection PyUnresolvedReferences
                from sentry_sdk import capture_exception
                capture_exception(e)
        return self

    def __exit__(self, *args):
        self.mattermost_connection.logout()

    def get_usernames_from_emails(self, emails: list[str]) -> list[str]:
        """
        Function that helps to get mattermost usernames from emails.

        :param emails: Emails of the users.
        :return: Mattermost usernames of the users.
        """
        usernames = []
        for email in emails:
            try:
                username = self.mattermost_connection.users.get_user_by_email(email).get('username')
                usernames.append(username)
            except HTTPError as e:
                # Log exception to Sentry if call fails, but do not break the server.
                if not settings.DEBUG:
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
            # Log exception to Sentry if call fails, but do not break the server.
            if not settings.DEBUG:
                # noinspection PyUnresolvedReferences
                from sentry_sdk import capture_exception
                capture_exception(e)


def create_mattermost_post(message: str, emails: list[str], channel: str = settings.MATTERMOST_CHANNEL) -> None:
    """
    Function that helps to create post in specific channel tagging the users
    in them.

    :param message: The message to be posted in mattermost.
    :param emails: Email ids of the users.
    :param channel: Channel, to which the message will be posted.
    """
    with Mattermost() as conn:
        tagged_usernames = [f'@{username}'
                            for username in conn.get_usernames_from_emails(emails)]
        if tagged_usernames:
            usernames = ', '.join(tagged_usernames)
            post = f'{usernames}: {message}'
            conn.post_message_to_channel(channel, post)
