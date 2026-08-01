from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("rides.urls")),
    path("api-token-auth/", obtain_auth_token, name="api-token-auth"),
]
