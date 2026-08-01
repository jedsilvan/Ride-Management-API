from rest_framework import serializers

from .models import Ride, RideEvent, User
from .serializers_lite import RideEventLiteSerializer, UserLiteSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "role", "first_name", "last_name", "email", "phone_number"]


class RideEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideEvent
        fields = ["id", "id_ride", "description", "created_at"]


class RideSerializer(serializers.ModelSerializer):
    """
    Read: nested rider/driver/today's-events for a rich response.
    Write: flat id_rider/id_driver FK ids to keep writes unambiguous.
    """

    id_rider = UserLiteSerializer(read_only=True)
    id_driver = UserLiteSerializer(read_only=True)
    id_rider_id = serializers.PrimaryKeyRelatedField(
        source="id_rider", queryset=User.objects.all(), write_only=True
    )
    id_driver_id = serializers.PrimaryKeyRelatedField(
        source="id_driver", queryset=User.objects.all(), write_only=True
    )
    todays_ride_events = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            "id",
            "status",
            "id_rider",
            "id_driver",
            "id_rider_id",
            "id_driver_id",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
            "todays_ride_events",
            "distance",
        ]

    def get_todays_ride_events(self, obj):
        # Populated by Prefetch(..., to_attr="todays_ride_events") in the
        # ViewSet's queryset. Falling back to an empty list keeps this
        # serializer safe to use even outside that optimized queryset
        # (e.g. in the detail view or in tests).
        events = getattr(obj, "todays_ride_events", None)
        if events is None:
            return []
        return RideEventLiteSerializer(events, many=True).data

    def get_distance(self, obj):
        # Only present when the queryset was annotated with a distance
        # expression (i.e. when ?ordering=distance was requested).
        value = getattr(obj, "distance", None)
        return round(value, 4) if value is not None else None
