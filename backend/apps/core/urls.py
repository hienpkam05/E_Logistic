from django.urls import path

from .views import ChoicesView, health

urlpatterns = [
    path("health/", health, name="health"),
    path("meta/choices/", ChoicesView.as_view(), name="meta-choices"),
]
