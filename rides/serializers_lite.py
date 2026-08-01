"""
Trimmed-down, read-only serializers used for nested representations
(rider, driver, ride events) inside the Ride list/detail response.
Keeping these separate from the "full" serializers avoids pulling in
fields (or triggering extra lookups) that the nested context doesn't need.
"""
from rest_framework import serializers

from .models import RideEvent, User


class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone_number"]
        read_only_fields = fields


class RideEventLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideEvent
        fields = ["id", "description", "created_at"]
        read_only_fields = fields
