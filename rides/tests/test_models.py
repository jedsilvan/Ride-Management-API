from django.test import TestCase
from django.utils import timezone

from rides.models import Ride, RideEvent, User


class ModelRelationshipTests(TestCase):
    def setUp(self):
        self.rider = User.objects.create(
            role="rider", first_name="Jane", last_name="Doe", email="jane@example.com"
        )
        self.driver = User.objects.create(
            role="driver", first_name="Chris", last_name="H", email="chris@example.com"
        )
        self.ride = Ride.objects.create(
            status="en-route",
            id_rider=self.rider,
            id_driver=self.driver,
            pickup_latitude=34.05,
            pickup_longitude=-118.25,
            dropoff_latitude=34.10,
            dropoff_longitude=-118.30,
            pickup_time=timezone.now(),
        )

    def test_rider_and_driver_are_distinguishable(self):
        self.assertEqual(self.rider.rides_as_rider.count(), 1)
        self.assertEqual(self.driver.rides_as_driver.count(), 1)
        self.assertEqual(self.rider.rides_as_driver.count(), 0)

    def test_ride_event_links_to_ride(self):
        event = RideEvent.objects.create(
            id_ride=self.ride,
            description="Status changed to pickup",
            created_at=timezone.now(),
        )
        self.assertIn(event, self.ride.ride_events.all())

    def test_ride_event_cascade_delete(self):
        RideEvent.objects.create(
            id_ride=self.ride, description="Status changed to pickup", created_at=timezone.now()
        )
        self.ride.delete()
        self.assertEqual(RideEvent.objects.count(), 0)
