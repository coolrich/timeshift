from django.urls import path
from ninja import NinjaAPI
from core.api import router
from core.auth import SessionOrToken

api = NinjaAPI(auth=SessionOrToken())
api.add_router("/time", router)

urlpatterns = [
    path("v1/", api.urls, name="api"),
]