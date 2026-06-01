import datetime
import pytest
import pytz
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.urls import reverse
from django.contrib.messages import get_messages
from django.test import override_settings

from core.models import VirtualClock
from logging import getLogger
from tests.conftest import USER_TEST_PASSWORD

logger = getLogger(__name__)

# ========================
# HELPERS
# ========================

@pytest.fixture
def auth_client(client, user):
    logger.debug(f"tests.accounts.test_accounts_views.auth_client():"
                 f"username={user.username} password={USER_TEST_PASSWORD}")
    logged_in = client.login(username=user.username, password=USER_TEST_PASSWORD)
    logger.debug(f"tests.accounts.test_accounts_views.auth_client():"
                 f"logged_in:{logged_in}")
    assert logged_in, "Login failed!"
    return client


# ========================
# SIGNUP
# ========================

@pytest.mark.django_db
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
    def test_signup_post_throttle_for_anonymous_ip(self, client):
        cache.clear()

        first_response = client.post(reverse("signup"), {})
        second_response = client.post(reverse("signup"), {})

        assert first_response.status_code == 200
        assert second_response.status_code == 429
        assert second_response["Retry-After"]


# ========================
# PROFILE
# ========================

@pytest.mark.django_db
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

@pytest.mark.django_db
class TestProfileClocks:

    def test_clocks_list(self, auth_client, user):
        clock = VirtualClock.objects.create(user_owner=user)

        response = auth_client.get(reverse("profile_clocks"))

        assert response.status_code == 200
        assert clock in response.context["clocks"]

    def test_html_elements(self, auth_client, user):
        clock = VirtualClock.objects.create(user_owner=user)

        response = auth_client.get(reverse("profile_clocks"))

        soup = BeautifulSoup(response.content, "html.parser")

        button = soup.find(
            "button",
            attrs={"onclick": f"copyApiLink('api-link-retrieve-clock-{clock.id}')"}
        )

        assert button is not None


# ========================
# CLOCK CONTROL
# ========================

@pytest.mark.django_db
class TestClockControl:

    def test_set_time(self, auth_client, user):
        clock = VirtualClock.objects.create(user_owner=user)

        now = "2011-11-04 00:05:23.283"

        response = auth_client.post(
            reverse("clock_control", args=[clock.id]),
            {"current_time": now},
            follow=True
        )

        assert response.status_code == 200

        tz = pytz.timezone(user.timezone)
        clock.refresh_from_db()

        expected = datetime.datetime.strptime(
            now, "%Y-%m-%d %H:%M:%S.%f"
        )

        assert clock.current_time == tz.localize(expected)

    def test_toggle_tick(self, auth_client, user):
        clock = VirtualClock.objects.create(user_owner=user)

        old_state = clock.tick_enabled

        auth_client.post(
            reverse("clock_control", args=[clock.id]),
            {"toggle_tick": "checkbox"}
        )

        clock.refresh_from_db()

        assert clock.tick_enabled != old_state

    def test_post_throttle_uses_global_scope(self, auth_client, user, free_plan):
        cache.clear()
        free_plan.throttle_rules.filter(scope="global").update(max_requests=1)
        clock = VirtualClock.objects.create(user_owner=user)

        first_response = auth_client.post(
            reverse("clock_control", args=[clock.id]),
            {"toggle_tick": "checkbox"}
        )
        second_response = auth_client.post(
            reverse("clock_control", args=[clock.id]),
            {"toggle_tick": "checkbox"}
        )

        assert first_response.status_code == 302
        assert second_response.status_code == 429
        assert second_response["Retry-After"]


# ========================
# ALLOWED USERS
# ========================

@pytest.mark.django_db
class TestAllowedUsers:

    @pytest.fixture(autouse=True)
    def setup(self, users_factory_sync, user):
        logger.debug(f"tests.accounts.test_accounts_views.TestAllowedUsers.setup():"
                     f"create stranger user")
        self.stranger = users_factory_sync(1, 10)[0]
        self.user = user

    def test_add_user(self, auth_client):
        stranger = self.stranger
        clock = VirtualClock.objects.create(user_owner=self.user)

        response = auth_client.post(
            reverse("clock_control", args=[clock.id]),
            {"add_user_id": stranger.id}
        )

        assert response.status_code == 200
        assert stranger in clock.allowed_users.all()

        messages = list(get_messages(response.wsgi_request))
        assert messages[0].message == f"Доступ надано: {stranger.username}"

    def test_remove_user(self, auth_client):
        stranger = self.stranger
        clock = VirtualClock.objects.create(user_owner=self.user)
        clock.allowed_users.add(stranger)
        assert stranger in clock.allowed_users.all()
        response = auth_client.post(
            reverse("clock_control", args=[clock.id]),
            {"remove_user_id": stranger.id}
        )

        assert response.status_code == 200
        assert stranger not in clock.allowed_users.all()
