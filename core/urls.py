from django.urls import path
from ninja import NinjaAPI
from core.api import router


api = NinjaAPI(version="1.0")
api.add_router("/", router)

urlpatterns = [
    path("v1/", api.urls, name="api"),
]