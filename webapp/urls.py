from django.urls import path

from .views import IndexView, DocsPageView, ContactsPageView

urlpatterns = [
    path("", IndexView.as_view(), name="home"),
    path("docs/", DocsPageView.as_view(), name="docs"),
    path("contacts/", ContactsPageView.as_view(), name="contacts")

]
