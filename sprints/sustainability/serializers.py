from rest_framework import serializers


# noinspection PyAbstractClass
class SustainabilityAccountSerializer(serializers.Serializer):
    """Serializer for Accounts."""
    key = serializers.CharField()
    name = serializers.CharField()
    overall = serializers.FloatField()
    by_cell = serializers.DictField()
    by_person = serializers.DictField()


# noinspection PyAbstractClass
class SustainabilityDashboardSerializer(serializers.Serializer):
    """Serializer for Sustainability Dashboard."""
    billable_accounts = SustainabilityAccountSerializer(many=True)
    non_billable_accounts = SustainabilityAccountSerializer(many=True)
    non_billable_responsible_accounts = SustainabilityAccountSerializer(many=True)
