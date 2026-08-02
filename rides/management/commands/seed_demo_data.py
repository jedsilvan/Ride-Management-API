from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from rides.models import Profile, Ride, RideEvent, User


class Command(BaseCommand):
    help = (
        "Seed demo data with dates computed relative to right now, so "
        "todays_ride_events and the bonus SQL report always have fresh, "
        "demoable data no matter when you run this."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing Ride/RideEvent/User rows before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()

        if options["flush"]:
            RideEvent.objects.all().delete()
            Ride.objects.all().delete()
            User.objects.all().delete()
            self.stdout.write("Cleared existing Ride/RideEvent/User rows.")

        # --- Users ---------------------------------------------------
        jane, _ = User.objects.update_or_create(
            email="jane@example.com",
            defaults={"role": "rider", "first_name": "Jane", "last_name": "Doe", "phone_number": "555-0101"},
        )
        mark, _ = User.objects.update_or_create(
            email="mark@example.com",
            defaults={"role": "rider", "first_name": "Mark", "last_name": "Lee", "phone_number": "555-0102"},
        )
        chris, _ = User.objects.update_or_create(
            email="chris@example.com",
            defaults={"role": "driver", "first_name": "Chris", "last_name": "Howard", "phone_number": "555-0201"},
        )
        randy, _ = User.objects.update_or_create(
            email="randy@example.com",
            defaults={"role": "driver", "first_name": "Randy", "last_name": "Wilson", "phone_number": "555-0202"},
        )
        howard, _ = User.objects.update_or_create(
            email="howard@example.com",
            defaults={"role": "driver", "first_name": "Howard", "last_name": "Yang", "phone_number": "555-0203"},
        )
        riders = [jane, mark]

        # --- Bonus report data: rides spread over the last 4 months ---
        # Same shape as the assessment doc's sample report: several
        # drivers, several months, several trips >1hr each.
        targets = [
            (3, "Chris H", 4), (3, "Howard Y", 5), (3, "Randy W", 2),
            (2, "Chris H", 7), (2, "Howard Y", 5),
            (1, "Chris H", 2), (1, "Howard Y", 2), (1, "Randy W", 11),
            (0, "Howard Y", 7), (0, "Randy W", 3),
        ]
        driver_map = {"Chris H": chris, "Randy W": randy, "Howard Y": howard}

        def month_back(dt, months):
            """Return (year, month) for `months` calendar months before dt."""
            m = dt.month - months
            y = dt.year
            while m <= 0:
                m += 12
                y -= 1
            return y, m

        ride_count = 0
        rider_idx = 0
        for months_ago, driver_label, count in targets:
            year, month = month_back(now, months_ago)
            for i in range(count):
                # explicit calendar construction -- never crosses into an
                # adjacent month, regardless of how many trips are in a bucket
                day = 2 + (i * 2) % 24  # stays within 2..26, safe for all months
                hour = 6 + (i % 12)
                duration_hours = 1.25 + (i % 5) * 0.5  # always > 1hr
                pickup_time = now.replace(
                    year=year, month=month, day=day, hour=hour, minute=0, second=0, microsecond=0
                )
                dropoff_time = pickup_time + timedelta(hours=duration_hours)

                rider = riders[rider_idx % 2]
                rider_idx += 1

                ride = Ride.objects.create(
                    status="dropoff",
                    id_rider=rider,
                    id_driver=driver_map[driver_label],
                    pickup_latitude=34.0 + (ride_count % 10) * 0.01,
                    pickup_longitude=-118.0 - (ride_count % 10) * 0.01,
                    dropoff_latitude=34.1 + (ride_count % 10) * 0.01,
                    dropoff_longitude=-118.1 - (ride_count % 10) * 0.01,
                    pickup_time=pickup_time,
                )
                RideEvent.objects.create(
                    id_ride=ride, description="Status changed to pickup", created_at=pickup_time
                )
                RideEvent.objects.create(
                    id_ride=ride, description="Status changed to dropoff", created_at=dropoff_time
                )
                ride_count += 1

        # --- A ride happening "right now", for the todays_ride_events demo ---
        recent_pickup = now - timedelta(hours=2)
        recent_ride = Ride.objects.create(
            status="en-route",
            id_rider=jane,
            id_driver=chris,
            pickup_latitude=34.05,
            pickup_longitude=-118.25,
            dropoff_latitude=34.10,
            dropoff_longitude=-118.30,
            pickup_time=recent_pickup,
        )
        RideEvent.objects.create(
            id_ride=recent_ride,
            description="Status changed to en-route",
            created_at=recent_pickup,
        )
        RideEvent.objects.create(
            id_ride=recent_ride,
            description="Status changed to pickup",
            created_at=now - timedelta(minutes=30),
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {ride_count + 1} rides ({ride_count} historical for the "
            f"bonus report, 1 recent for todays_ride_events -- ride id "
            f"{recent_ride.id})."
        ))