import django_filters

from .models import Ride


class RideFilter(django_filters.FilterSet):
    """
    Supports:
      ?status=en-route
      ?rider_email=jane@example.com
    Both resolve to a single indexed lookup -- rider_email traverses the
    id_rider FK (already select_related in the view), so it doesn't add
    a query.
    """

    rider_email = django_filters.CharFilter(
        field_name="id_rider__email", lookup_expr="iexact"
    )

    class Meta:
        model = Ride
        fields = ["status", "rider_email"]
