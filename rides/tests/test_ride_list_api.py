from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from rides.models import Profile, Ride, RideEvent, User


class RideListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        auth_user_model = get_user_model()
        self.admin_auth_user = auth_user_model.objects.create_user(
            username="admin", password="password"
        )
        Profile.objects.create(user=self.admin_auth_user, role="admin")
        self.client.force_authenticate(user=self.admin_auth_user)

        self.rider = User.objects.create(
            role="rider", first_name="Jane", last_name="Doe", email="jane@example.com"
        )
        self.driver = User.objects.create(
            role="driver", first_name="Chris", last_name="H", email="chris@example.com"
        )

        now = timezone.now()
        self.rides = []
        for i in range(5):
            ride = Ride.objects.create(
                status="en-route" if i % 2 == 0 else "dropoff",
                id_rider=self.rider,
                id_driver=self.driver,
                pickup_latitude=34.0 + i,
                pickup_longitude=-118.0 - i,
                dropoff_latitude=34.1 + i,
                dropoff_longitude=-118.1 - i,
                pickup_time=now - timedelta(hours=i),
            )
            self.rides.append(ride)
            # one recent event (within 24h) and one stale event (outside 24h)
            RideEvent.objects.create(
                id_ride=ride, description="Status changed to pickup", created_at=now - timedelta(hours=1)
            )
            RideEvent.objects.create(
                id_ride=ride, description="Status changed to dropoff", created_at=now - timedelta(days=5)
            )

    def test_list_requires_admin(self):
        anon_client = APIClient()
        response = anon_client.get("/api/rides/")
        self.assertEqual(response.status_code, 401)

    def test_list_returns_rides_with_nested_data(self):
        response = self.client.get("/api/rides/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 5)
        first = response.data["results"][0]
        self.assertIn("id_rider", first)
        self.assertIn("id_driver", first)
        self.assertIn("todays_ride_events", first)

    def test_todays_ride_events_excludes_stale_events(self):
        response = self.client.get("/api/rides/")
        first = response.data["results"][0]
        # only the recent event should appear, not the 5-day-old one
        self.assertEqual(len(first["todays_ride_events"]), 1)
        self.assertEqual(first["todays_ride_events"][0]["description"], "Status changed to pickup")

    def test_filter_by_status(self):
        response = self.client.get("/api/rides/?status=en-route")
        self.assertEqual(response.data["count"], 3)

    def test_filter_by_rider_email(self):
        response = self.client.get("/api/rides/?rider_email=jane@example.com")
        self.assertEqual(response.data["count"], 5)

    def test_ordering_by_pickup_time(self):
        response = self.client.get("/api/rides/?ordering=pickup_time")
        times = [r["pickup_time"] for r in response.data["results"]]
        self.assertEqual(times, sorted(times))

    def test_ordering_by_distance_requires_coordinates(self):
        response = self.client.get("/api/rides/?ordering=distance")
        self.assertEqual(response.status_code, 400)

    def test_ordering_by_distance(self):
        response = self.client.get(
            "/api/rides/?ordering=distance&pickup_lat=34.0&pickup_lng=-118.0"
        )
        self.assertEqual(response.status_code, 200)
        distances = [r["distance"] for r in response.data["results"]]
        self.assertEqual(distances, sorted(distances))

    def test_query_count_stays_within_budget(self):
        # 1 COUNT + 1 ride/rider/driver join + 1 scoped ride_event fetch = 3
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/rides/")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx.captured_queries), 3)
