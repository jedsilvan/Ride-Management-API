from django.conf import settings
from django.db import models


class Profile(models.Model):
    """
    Links a Django auth user (the account that actually logs in and
    calls the API) to a role used for permission checks. Kept separate
    from `User` below, which represents riders/drivers as ride data --
    not every rider/driver has API login access, but every admin caller
    needs one of these.
    """

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("rider", "Rider"),
        ("driver", "Driver"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)

    class Meta:
        db_table = "profile"

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class User(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("rider", "Rider"),
        ("driver", "Driver"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "user"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


class Ride(models.Model):
    STATUS_CHOICES = [
        ("en-route", "En Route"),
        ("pickup", "Pickup"),
        ("dropoff", "Dropoff"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    id_rider = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="rides_as_rider"
    )
    id_driver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="rides_as_driver"
    )
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride"
        indexes = [
            models.Index(fields=["status", "pickup_time"], name="ride_status_pickup_idx"),
        ]

    def __str__(self):
        return f"Ride #{self.id} ({self.status})"


class RideEvent(models.Model):
    id_ride = models.ForeignKey(
        Ride, on_delete=models.CASCADE, related_name="ride_events"
    )
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "ride_event"
        indexes = [
            models.Index(fields=["id_ride", "created_at"], name="rideevent_ride_created_idx"),
            models.Index(fields=["id_ride", "description"], name="rideevent_ride_desc_idx"),
        ]

    def __str__(self):
        return f"RideEvent #{self.id} for Ride #{self.id_ride_id}"
