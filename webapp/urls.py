from django.urls import path
# from .views import home_page_view
from .views import IndexView, AboutPageView
from django.contrib import admin

urlpatterns = [
    path("", IndexView.as_view(), name="home"),

]
