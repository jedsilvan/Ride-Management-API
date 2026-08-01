from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Grants access only to authenticated users whose linked Profile has
    role == 'admin'. A user with no Profile at all (e.g. a superuser
    created without one) is denied rather than raising an error.
    """

    message = "Only users with the 'admin' role can access this endpoint."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return self._get_role(user) == "admin"

    @staticmethod
    def _get_role(user):
        profile = getattr(user, "profile", None)
        return profile.role if profile else None
