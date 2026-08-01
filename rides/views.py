from datetime import timedelta

from django.db.models import ExpressionWrapper, F, FloatField, Prefetch
from django.db.models.functions import Power, Sqrt
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from .filters import RideFilter
from .models import Ride, RideEvent, User
from .permissions import IsAdminRole
from .serializers import RideEventSerializer, RideSerializer, UserSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]


class RideEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RideEvent.objects.all().order_by("-created_at")
    serializer_class = RideEventSerializer
    permission_classes = [IsAdminRole]


class RideViewSet(viewsets.ModelViewSet):
    """
    Ride list/detail/CRUD.

    Query budget for the list endpoint:
      1) COUNT(*) for pagination
      2) Ride JOIN rider JOIN driver, for the current page
      3) RideEvent WHERE id_ride IN (page ids) AND created_at >= last 24h

    That budget holds no matter how large `ride` or `ride_event` grow,
    because #3 is scoped by both the page's ride ids and a time window
    instead of ever pulling a ride's full event history.
    """

    serializer_class = RideSerializer
    permission_classes = [IsAdminRole]
    filterset_class = RideFilter

    ORDERING_FIELDS = {"pickup_time", "-pickup_time", "distance", "-distance"}

    def get_queryset(self):
        last_24h = timezone.now() - timedelta(hours=24)

        queryset = Ride.objects.select_related("id_rider", "id_driver").prefetch_related(
            Prefetch(
                "ride_events",
                queryset=RideEvent.objects.filter(created_at__gte=last_24h).order_by(
                    "-created_at"
                ),
                to_attr="todays_ride_events",
            )
        )

        ordering = self.request.query_params.get("ordering")
        if ordering:
            if ordering not in self.ORDERING_FIELDS:
                raise ValidationError(
                    {
                        "ordering": (
                            "Must be one of: pickup_time, -pickup_time, "
                            "distance, -distance"
                        )
                    }
                )

            if ordering.lstrip("-") == "distance":
                queryset = self._annotate_distance(queryset)

            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("pickup_time")

        return queryset

    def _annotate_distance(self, queryset):
        lat = self.request.query_params.get("pickup_lat")
        lng = self.request.query_params.get("pickup_lng")

        if lat is None or lng is None:
            raise ValidationError(
                "pickup_lat and pickup_lng are required when ordering by distance."
            )

        try:
            lat, lng = float(lat), float(lng)
        except ValueError as exc:
            raise ValidationError("pickup_lat and pickup_lng must be numeric.") from exc

        # Equirectangular approximation: computed in SQL, index-friendly,
        # and accurate enough at city scale. Avoids trig functions so it
        # stays fast at large table sizes. Swap for PostGIS in production
        # if true great-circle distance / spatial indexing is needed.
        return queryset.annotate(
            distance=ExpressionWrapper(
                Sqrt(
                    Power(F("pickup_latitude") - lat, 2)
                    + Power(F("pickup_longitude") - lng, 2)
                ),
                output_field=FloatField(),
            )
        )
