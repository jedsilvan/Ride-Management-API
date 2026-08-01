from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from rides.models import Profile
from rides.permissions import IsAdminRole


class IsAdminRoleTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsAdminRole()
        self.auth_user_model = get_user_model()

    def _request_with_user(self, user):
        request = self.factory.get("/api/rides/")
        request.user = user
        return request

    def test_anonymous_user_denied(self):
        request = self._request_with_user(AnonymousUser())
        self.assertFalse(self.permission.has_permission(request, None))

    def test_authenticated_user_without_profile_denied(self):
        user = self.auth_user_model.objects.create_user(username="noprofile", password="pw")
        request = self._request_with_user(user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_authenticated_non_admin_denied(self):
        user = self.auth_user_model.objects.create_user(username="rider1", password="pw")
        Profile.objects.create(user=user, role="rider")
        request = self._request_with_user(user)
        self.assertFalse(self.permission.has_permission(request, None))

    def test_authenticated_admin_allowed(self):
        user = self.auth_user_model.objects.create_user(username="admin1", password="pw")
        Profile.objects.create(user=user, role="admin")
        request = self._request_with_user(user)
        self.assertTrue(self.permission.has_permission(request, None))
