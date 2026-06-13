import datetime
from logging import getLogger

import pytest
import pytz
from bs4 import BeautifulSoup
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.http import HttpRequest, QueryDict, HttpResponse
from django.test import override_settings
from django.urls import reverse
from django.views import View

from accounts.mixins import PostRateLimitMixin
from accounts.models import ThrottleRule
from django_project.urls import urlpatterns
from tests.conftest import auth_client

logger = getLogger(__name__)

# ========================
# SIGNUP
# ========================

@pytest.mark.django_db(transaction=True)
class TestSignUpView:

    @pytest.fixture(autouse=True)
    def set_free_plan(self, free_plan):
        logger.debug(f"tests.accounts.test_accounts_views.TestSignUpView.set_free_plan():"
                     f"set free plan")

    def test_signup_get(self, client):
        response = client.get(reverse("signup"))

        assert response.status_code == 200
        assert "registration/signup.html" in [t.name for t in response.templates]
        assert "form" in response.context

    def test_signup_post(self, client):
        data = {
            "username": "newuser",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
            "email": "newuser@example.com",
            "phone_number": "+380687807356",
        }

        response = client.post(reverse("signup"), data)

        assert response.status_code == 302
        assert response.url == reverse("profile_dashboard")

    @override_settings(NINJA_THROTTLE_RATES={"global": "1/m", "clock_create": "5/m"})
    @pytest.mark.django_db(transaction=True)
    def test_signup_post_throttle_for_anonymous_ip(self, client):
        cache.clear()

        # logger.debug('tests.accounts.test_accounts_views.TestSignUpView.test_signup_post_throttle_for_anonymous_ip:'
        #              f'client headers: {client}')
        logger.debug('tests.accounts.test_accounts_views.TestSignUpView.test_signup_post_throttle_for_anonymous_ip'
                     f" cache: {cache.get(f"throttle:global:ip:{client.headers}")}")
        first_response = client.post(reverse("signup"), {})
        second_response = client.post(reverse("signup"), {})

        assert first_response.status_code == 200
        assert second_response.status_code == 429
        assert second_response["Retry-After"]


# ========================
# PROFILE
# ========================

@pytest.mark.django_db(transaction=True)
class TestProfileDashboard:

    def test_requires_login(self, client):
        response = client.get(reverse("profile_dashboard"))

        assert response.status_code == 302
        assert "login" in response.url

    def test_profile(self, auth_client):
        response = auth_client.get(reverse("profile_dashboard"), follow=True)

        assert response.status_code == 200
        logger.debug(f"tests.accounts.test_accounts_views.TestProfileDashboard.test_profile():"
                     f"response.templates: {[t.name for t in response.templates]}")
        assert "accounts/dashboard.html" in [t.name for t in response.templates]
        assert "total_clocks" in response.context
        assert "latest_clock" in response.context


# ========================
# CLOCKS
# ========================

@pytest.mark.django_db(transaction=True)
class TestProfileClocks:
    def test_clocks_list(self, auth_client, user, owned_clock):
        # clock = VirtualClock.objects.create(user_owner=user)

        response = auth_client.get(reverse("profile_clocks"))

        assert response.status_code == 200
        assert owned_clock in response.context["clocks"]

    def test_html_elements(self, auth_client, owned_clock):
        # clock = VirtualClock.objects.create(user_owner=user)

        response = auth_client.get(reverse("profile_clocks"))

        soup = BeautifulSoup(response.content, "html.parser")

        button = soup.find(
            "button",
            attrs={"onclick": f"copyApiLink('api-link-retrieve-clock-{owned_clock.id}')"}
        )

        assert button is not None


# ========================
# CLOCK CONTROL
# ========================

@pytest.mark.django_db(transaction=True)
class TestClockControl:

    def test_set_time(self, auth_client, owned_clock, clock_control_url):
        # clock = VirtualClock.objects.create(user_owner=user)

        now = "2011-11-04 00:05:23.283"

        response = auth_client.post(
            reverse("clock_control", args=[owned_clock.id]),
            # clock_control_url(owned_clock.id),
            {"current_time": now},
            follow=True
        )

        assert response.status_code == 200

        tz = pytz.timezone(owned_clock.user_owner.timezone)
        owned_clock.refresh_from_db()

        expected = datetime.datetime.strptime(
            now, "%Y-%m-%d %H:%M:%S.%f"
        )

        assert owned_clock.current_time == tz.localize(expected)

    def test_toggle_tick(self, auth_client, owned_clock):
        # clock = VirtualClock.objects.create(user_owner=user)

        old_state = owned_clock.tick_enabled

        auth_client.post(
            reverse("clock_control", args=[owned_clock.id]),
            {"toggle_tick": "checkbox"}
        )

        owned_clock.refresh_from_db()

        assert owned_clock.tick_enabled != old_state

    def test_post_throttle_uses_global_scope(self, auth_client, owned_clock, free_plan):
        cache.clear()
        free_plan.throttle_rules.filter(scope="global").update(max_requests=1)
        # clock = VirtualClock.objects.create(user_owner=user)

        first_response = auth_client.post(
            reverse("clock_control", args=[owned_clock.id]),
            {"toggle_tick": "checkbox"}
        )
        second_response = auth_client.post(
            reverse("clock_control", args=[owned_clock.id]),
            {"toggle_tick": "checkbox"}
        )

        assert first_response.status_code == 302
        assert second_response.status_code == 429
        assert second_response["Retry-After"]


# ========================
# ALLOWED USERS
# ========================

@pytest.mark.django_db(transaction=True)
class TestAllowedUsers:

    @pytest.fixture(autouse=True)
    def setup(self, users_factory_sync, user):
        logger.debug(f"tests.accounts.test_accounts_views.TestAllowedUsers.setup():"
                     f"create stranger user")
        self.stranger = users_factory_sync(1, 10)[0]
        self.user = user

    def test_add_user(self, auth_client, owned_clock):
        stranger = self.stranger
        # clock = VirtualClock.objects.create(user_owner=self.user)

        response = auth_client.post(
            reverse("clock_control", args=[owned_clock.id]),
            {"add_user_id": stranger.id}
        )

        assert response.status_code == 200
        assert stranger in owned_clock.allowed_users.all()

        messages = list(get_messages(response.wsgi_request))
        assert messages[0].message == f"Доступ надано: {stranger.username}"

    def test_remove_user(self, auth_client, owned_clock):
        stranger = self.stranger
        # clock = VirtualClock.objects.create(user_owner=self.user)
        owned_clock.allowed_users.add(stranger)
        assert stranger in owned_clock.allowed_users.all()
        response = auth_client.post(
            reverse("clock_control", args=[owned_clock.id]),
            {"remove_user_id": stranger.id}
        )

        assert response.status_code == 200
        assert stranger not in owned_clock.allowed_users.all()


class _TestView(PostRateLimitMixin, View):
    throttle_scope = ThrottleRule.Scope.GLOBAL
    def post(self, request, *args, **kwargs):
        logger.debug("tests.accounts.test_accounts_views.TestPostRateLimitMixin._TestView.post():"
                     f"request:{request}")
        return HttpResponse("Post done!")


@pytest.mark.django_db(transaction=True)
@pytest.mark.urls('tests.accounts.test_urls')
class TestPostRateLimitMixin:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client):
        cache.clear()
        logger.debug(f"tests.accounts.test_accounts_views.TestPostRateLimitMixin.setup():")
        self.client = auth_client
        self.tv = _TestView()
        logger.debug(f"tests.accounts.test_accounts_views.TestPostRateLimitMixin.setup():"
                     f" urlpatterns: {urlpatterns}")
        yield
        cache.clear()

    def test_dispatch_success(self):
        logger.debug(f'tests.accounts.test_accounts_views.TestPostRateLimitMixin.test_dispatch_success():')
        req = HttpRequest()
        req.method = "POST"
        req.POST = QueryDict("test=true")
        r = self.tv.dispatch(req)
        logger.debug("tests.accounts.test_accounts_views.TestPostRateLimitMixin.test_dispatch()"
                     f" response:{r}")
        assert r.status_code == 200
        r = self.client.post(reverse('test_mixin'))
        assert r.status_code == 200

    def test_dispatch_failure(self, mocker):
        # RateLimitService.check_request = mocker.MagicMock(return_value=(False, 1, 'm'))
        with mocker.patch('accounts.services.rate_limit.RateLimitService.check_request',
                          mocker.MagicMock(return_value=(False, 1, 'm'))):
            logger.debug(f'tests.accounts.test_accounts_views.TestPostRateLimitMixin.test_dispatch_failure():')
            req = HttpRequest()
            req.method = "POST"
            req.POST = QueryDict("test=true")
            r = self.tv.dispatch(req)
            logger.debug("tests.accounts.test_accounts_views.TestPostRateLimitMixin.test_dispatch()"
                         f" response:{r}")
            assert r.status_code == 429
            r = self.client.post(reverse('test_mixin'))
            assert r.status_code == 429
