from django.urls import path

from core.api import api

urlpatterns = [
    path("v1/", api.urls, name="api"),
]





