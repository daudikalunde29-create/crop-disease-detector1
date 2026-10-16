from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]

handler404 = "api.health.not_found"
handler500 = "api.health.server_error"
