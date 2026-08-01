from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RideEventViewSet, RideViewSet, UserViewSet

router = DefaultRouter()
router.register(r"rides", RideViewSet, basename="ride")
router.register(r"users", UserViewSet, basename="user")
router.register(r"ride-events", RideEventViewSet, basename="ride-event")

urlpatterns = [
    path("", include(router.urls)),
]
