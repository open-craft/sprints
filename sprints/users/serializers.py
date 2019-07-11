from django.contrib.auth import get_user_model
from rest_framework import serializers

UserModel = get_user_model()


class UserDetailsSerializer(serializers.ModelSerializer):
    """
    User serializer used by JWT.
    """

    class Meta:
        model = UserModel
        fields = ('pk', 'email', 'is_staff')
        read_only_fields = fields
