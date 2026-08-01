from django.contrib import admin

from .models import Profile, Ride, RideEvent, User


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "role"]
    list_filter = ["role"]
    search_fields = ["user__username", "user__email"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "first_name", "last_name", "email", "role"]
    list_filter = ["role"]
    search_fields = ["first_name", "last_name", "email"]


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "id_rider", "id_driver", "pickup_time"]
    list_filter = ["status"]
    autocomplete_fields = []


@admin.register(RideEvent)
class RideEventAdmin(admin.ModelAdmin):
    list_display = ["id", "id_ride", "description", "created_at"]
    list_filter = ["description"]
