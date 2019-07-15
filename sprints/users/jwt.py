from rest_framework_jwt.utils import jwt_payload_handler


def jwt_payload_handler_custom(user):
    """Include custom data in JWT token."""
    payload = jwt_payload_handler(user)
    payload['email'] = user.email
    payload['is_staff'] = user.is_staff
    return payload
