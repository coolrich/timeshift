from django.urls import path
from .views import home_page_view

urlpatterns = [
    path("", home_page_view, name="home"),
    # path("home/", home_page_view, name="home"),
]
