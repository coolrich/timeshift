from django.urls import path

from tests.accounts.test_accounts_views import _TestView

urlpatterns = [path("test/", _TestView.as_view(), name='test_mixin')]
