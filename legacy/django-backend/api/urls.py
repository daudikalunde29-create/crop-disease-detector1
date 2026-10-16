from django.urls import include, path

from .health import health
from apps.accounts.views import ProfileView

urlpatterns = [
    path("health/", health, name="health"),
    path("auth/", include("apps.accounts.urls")),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("predict/", include("apps.predictions.urls")),
]
