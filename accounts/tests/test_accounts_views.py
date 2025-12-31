import datetime
from http.client import responses
from logging import getLogger

import pytz
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from core.models import VirtualClock
from core.services import VirtualClockController

logger = getLogger(__name__)
User = get_user_model()


class SignUpViewTests(TestCase):

    def test_signup_get_renders_form(self):
        url = reverse("signup")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/signup.html")
        self.assertIn("form", response.context)

    def test_signup_post_creates_and_logs_in_user(self):
        url = reverse("signup")
        data = {
            "username": "newuser",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
            "email": "newuser@example.com",
            "phone_number": "+380687807356"
        }
        response = self.client.post(url, data)
        logger.debug(f"Response: {response.content.decode()}")
        # перевіряємо, що редірект на profile
        self.assertRedirects(response, reverse("profile_dashboard"))
        # користувач створений
        self.assertTrue(User.objects.get(username="newuser"))
        # користувач залогінений
        user = User.objects.get(username="newuser")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)


class ProfileDashboardViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily", password="verySecret123!")
        self.url = reverse("profile_dashboard")
        self.client.login(username="emily", password="verySecret123!")

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        # редірект на login з next=
        login_url = reverse("login")
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_profile_shows_virtual_clocks(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard.html")
        # у контексті є virtual_clocks
        self.assertIn("total_clocks", response.context)
        self.assertIn("latest_clock", response.context)

    def test_check_for_correct_token(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard.html")
        self.assertIn("user", response.context)
        self.assertEqual(response.context["user"].api_token, self.user.api_token)


class ProfileTokensViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily", password="verySecret123!")
        VirtualClock.objects.create(user_owner=self.user)
        self.client.login(username="emily", password="verySecret123!")
        self.url = reverse("profile_tokens")

    def test_profile_tokens_context(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/tokens.html")
        self.assertIn("user", response.context)
        self.assertIn("virtual_clocks", response.context)


class ProfileClocksViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily", password="verySecret123!")
        VirtualClock.objects.create(user_owner=self.user)
        self.client.login(username="emily", password="verySecret123!")
        self.url = reverse("profile_clocks")

    def test_profile_clocks_context(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/clocks.html")
        self.assertIn("clocks", response.context)
        self.assertQuerySetEqual(response.context["clocks"], VirtualClock.objects.filter(user_owner=self.user))


class ClockDetailViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily", password="verySecret123!")
        self.clock = VirtualClock.objects.create(user_owner=self.user)
        self.client.login(username="emily", password="verySecret123!")
        self.url = reverse("clock_detail", args=[self.clock.id])

    def test_clock_detail_context(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/clock_detail.html")
        self.assertIn("clock", response.context)
        self.assertEqual(response.context["clock"], self.clock)
        self.assertIn(response.context["clock"], VirtualClock.objects.filter(user_owner=self.user))


class ClockCreateViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily", password="verySecret123!")
        self.client.login(username="emily", password="verySecret123!")
        self.url = reverse("clock_create")

    def test_create_view_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_post_creates_clock(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VirtualClock.objects.count(), 1)

    def test_post_creates_clock_with_name(self):
        response = self.client.post(self.url, {"name": "Test Clock"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VirtualClock.objects.count(), 1)
        self.assertEqual(VirtualClock.objects.first().name, "Test Clock")

    def test_clock_create_view_redirects_to_profile_clocks(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profile_clocks"))

    def test_clock_create_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/clock_create.html")
        self.assertIn("form", response.context)
        self.assertIn("name", response.context["form"].fields)


class ClockDeleteViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily", password="verySecret123!")
        self.clock = VirtualClock.objects.create(user_owner=self.user)
        self.client.login(username="emily", password="verySecret123!")
        self.url = reverse("clock_delete", args=[self.clock.id])

    def test_delete_view_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_delete_view_post_deletes_clock(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VirtualClock.objects.count(), 0)

    def test_delete_view_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/clock_confirm_delete.html")

    def test_delete_view_redirects_to_profile_clocks(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profile_clocks"))

    def test_user_cannot_delete_someone_elses_clock(self):
        other = User.objects.create_user(username="john", password="12345")
        self.client.logout()
        self.client.login(username="john", password="12345")
        self.assertEqual(VirtualClock.objects.filter(user_owner=other).count(), 0)
        response = self.client.post(self.url)
        logger.debug(f"Response: {response}")
        # self.assertEqual(response.status_code, 404)  # або 403 — залежно від твоєї реалізації


class ProfileSettingsViewTest(TestCase):
    def setUp(self):
        self.un = "emily"
        self.ps = "verySecret123!"
        self.tz = "Europe/Kyiv"
        self.em = "emily@example.com"
        self.pn = "+380969817231"
        self.user = User.objects.create_user(username=self.un, password=self.ps, timezone=self.tz, email=self.em,
                                             phone_number=self.pn)
        self.client.login(username=self.un, password=self.ps)
        self.url = reverse("profile_settings")

    def test_profile_settings_context(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/settings.html")
        self.assertIn("user", response.context)

    def test_profile_settings_message(self):
        logger.debug(f"test_profile_notifications()")
        # response = self.client.get(self.url)
        r = self.client.post(self.url, {
            'username': self.un,
            'timezone': self.tz,
            'email': self.em,
            'phone_number': self.pn
        }, follow=True)
        # logger.debug(f"Response: {response.content.decode()}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Налаштування збережено.")

    def test_post_without_required_fields(self):
        logger.debug(f"test_required_fields()")
        r = self.client.post(self.url)
        # logger.debug(f"Response r.context.get('form').errors: {help(r.context.get('form').errors)}")
        # logger.debug(f"Response: {r.context.get('form').errors.get_json_data()}")
        field_details = r.context.get('form').errors.get_json_data().items()
        form = r.context.get('form')
        for field_name, details in field_details:
            self.assertFormError(form,
                                 field_name,
                                 details[0]['message'])


class ClockControlViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emily", password="verySecret123!")
        self.user1 = User.objects.create_user(username="emily1", password="verySecret123!")
        self.clock = VirtualClock.objects.create(user_owner=self.user)
        self.client.login(username="emily", password="verySecret123!")
        self.url = reverse("clock_control", args=[self.clock.id])
        self.next = reverse("clock_detail", args=[self.clock.id])

    def test_control_view_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_view_edits_time_success(self):
        now = '2011-11-04 00:05:23.283'
        now_dt = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S.%f")
        # logger.debug(f"Current time: {now}")
        response = self.client.post(self.url,
                                    {"current_time": now, 'next': self.next},
                                    follow=True)
        logger.debug(f"response: {response.redirect_chain}")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/clock_detail.html")
        # self.assertRedirects(response, reverse("clock_detail", args=[self.clock.id]))
        self.assertContains(response, now)
        tz = pytz.timezone(self.user.timezone)
        clock = VirtualClock.objects.get(pk=self.clock.pk)
        self.assertEqual(clock.current_time, tz.localize(now_dt))

    def test_view_edits_time_failure(self):
        now = 'invalid_time'
        response = self.client.post(self.url,
                                    {"current_time": now},
                                    )
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, "accounts/clock_detail.html")
        logger.debug(f"Response: {response.content.decode()}")
        self.assertRaises(ValueError)
        self.assertContains(response, "Не вдалося встановити час. Перевірте правильність формату", status_code=400)

    def test_control_view_post_toggle_tick(self):
        old_state = self.clock.tick_enabled
        response = self.client.post(self.url, data={'toggle_tick': 'toggle_tick'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(VirtualClock.objects.count(), 1)
        self.assertNotEqual(VirtualClock.objects.first().tick_enabled, old_state)

    def test_control_view_post_tick_enabled(self):
        old_state = self.clock.tick_enabled
        response = self.client.post(self.url, data={'tick_enabled': 'on'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(VirtualClock.objects.count(), 1)
        self.assertNotEqual(VirtualClock.objects.first().tick_enabled, old_state)

    def test_control_view_post_set_clock_name(self):
        old_name = self.clock.name
        response = self.client.post(self.url, data={'clock_name': 'New Clock Name'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(VirtualClock.objects.count(), 1)
        self.assertNotEqual(VirtualClock.objects.first().name, old_name)

    def test_control_view_post_add_user_success(self):
        response = self.client.post(self.url, data={'add_user_id': self.user1.id})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "includes/allowed_users_table.html")
        self.assertContains(response, self.user1.username)
        # logger.debug(f"Response: {response.content.decode()}")
        self.assertContains(response, f"Забрати доступ")
        self.assertIn(self.user1, self.clock.allowed_users.all())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages)
        self.assertEqual(messages[0].message, f"Доступ надано: {self.user1.username}")

    def test_control_view_post_add_user_failure(self):
        response = self.client.post(self.url, data={'add_user_id': self.user1.id + 1}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.user1.username)
        # self.clock.refresh_from_db()
        self.assertNotIn(self.user1, self.clock.allowed_users.all())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages)
        self.assertEqual(messages[0].message, f"Користувача з таким ID не існує")

    def test_control_view_post_add_user_already_have_access(self):
        self.clock.allowed_users.add(self.user1)
        response = self.client.post(self.url, data={'add_user_id': self.user1.id})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "includes/allowed_users_table.html")
        self.assertContains(response, self.user1.username)
        # logger.debug(f"Response: {response.content.decode()}")
        self.assertContains(response, f"Забрати доступ")
        self.assertIn(self.user1, self.clock.allowed_users.all())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages)
        self.assertEqual(messages[0].message, f"Користувач уже має доступ")

    def test_control_view_post_remove_user_success(self):
        self.clock.allowed_users.add(self.user1)
        response = self.client.post(self.url, data={'remove_user_id': self.user1.id})
        self.assertTemplateUsed(response, "includes/allowed_users_table.html")
        # self.assertContains(response, self.user1.username)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages)
        self.assertEqual(messages[0].message, f"Користувача {self.user1.username} з ID {self.user1.id} видалено")

    def test_control_view_post_remove_user_failure(self):
        self.clock.allowed_users.add(self.user1)
        response = self.client.post(self.url, data={'remove_user_id': self.user1.id + 1})
        logger.debug(f"Response: {response.content.decode()}")
        self.assertTemplateUsed(response, "includes/allowed_users_table.html")
        # self.assertContains(response, self.user1.username)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages)
        self.assertEqual(messages[0].message, f"Користувача з таким ID не існує")


class UserTokenUpdateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emily",
                                             password="verySecret123!",
                                             email="emily@example.com",
                                             phone_number="+380969817231")
        self.client.login(username="emily", password="verySecret123!")
        self.url = reverse("user_token_update")

    def test_update_user_api_token_view(self):
        old_token = self.user.api_token
        r = self.client.post(self.url, {"refresh_token": True})
        # logger.debug(f"test_update_user_api_token_view():  self.client.post: response:\n{r}")
        self.assertEqual(r.status_code, 302)
        self.user.refresh_from_db()
        self.assertNotEqual(old_token, self.user.api_token)


class UserSearchViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emily",
                                             password="verySecret123!",
                                             email="emily@example.com",
                                             phone_number="+380969817231")
        self.user1 = User.objects.create_user(username="emily1",
                                              password="rdIGn654^*fFers",
                                              email="emily1@example.com",
                                              phone_number="+380969817231")
        self.client.login(username="emily", password="verySecret123!")
        self.clock = VirtualClock.objects.create(user_owner=self.user)
        self.url = reverse("user_search_by_id", args=[self.clock.id])

    def test_user_search_view_not_found_by_id(self):
        logger.debug(f"accounts.tests.test_accounts_views."
                     f"UserSearchByIdViewTest.test_user_search_by_id_view_not_found:"
                     f"url: {self.url}")
        response = self.client.get(self.url, {"user_id": self.user1.id+1},
                                   HTTP_HX_REQUEST="true",
                                   )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "includes/user_search_by_id.html")
        logger.debug(f"accounts.tests.test_accounts_view.UserSearchByIdViewTest."
                     f"test_user_search_by_id_view(): {response.content.decode()}")
        self.assertNotContains(response, self.user1.username)
        self.assertContains(response, "Користувача з таким ID не знайдено або доступ уже є")

    def test_user_search_view_found_by_id(self):
        response = self.client.get(self.url, {"user_id": self.user1.id},
                                   HTTP_HX_REQUEST="true",
                                   )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "includes/user_search_by_id.html")
        logger.debug(f"accounts.tests.test_accounts_view.UserSearchByIdViewTest."
                     f"test_user_search_by_id_view(): {response.content.decode()}")
        self.assertContains(response, self.user1.username)
        self.assertContains(response, f"Знайдено: <strong>{self.user1.username}</strong> (ID {self.user1.id})")

    def test_user_search_view_empty_search_field(self):
        response = self.client.get(self.url, {"user_id": ""},
                                   HTTP_HX_REQUEST="true",
                                   )
        self.assertEqual(response.status_code, 200)
        # self.assertTemplateUsed(response, "includes/user_search_by_id.html")
        logger.debug(f"accounts.tests.test_accounts_view.UserSearchByIdViewTest."
                     f"test_user_search_by_id_view(): {response.content.decode()}")
        self.assertContains(response, "")

    def test_user_search_view_not_found_by_name(self):
        logger.debug(f"accounts.tests.test_accounts_views."
                     f"UserSearchByIdViewTest.test_user_search_by_id_view_not_found:"
                     f"url: {self.url}")
        response = self.client.get(self.url, {"user_id": self.user1.username + "1"},
                                   HTTP_HX_REQUEST="true",
                                   )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "includes/user_search_by_id.html")
        logger.debug(f"accounts.tests.test_accounts_view.UserSearchByIdViewTest."
                     f"test_user_search_by_id_view(): {response.content.decode()}")
        self.assertNotContains(response, self.user1.username)
        self.assertContains(response, "Користувача з таким ID не знайдено або доступ уже є")

    def test_user_search_view_found_by_name(self):
        response = self.client.get(self.url, {"user_id": self.user1.username},
                                   HTTP_HX_REQUEST="true",
                                   )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "includes/user_search_by_id.html")
        logger.debug(f"accounts.tests.test_accounts_view.UserSearchByIdViewTest."
                     f"test_user_search_by_id_view(): {response.content.decode()}")
        self.assertContains(response, self.user1.username)
        self.assertContains(response, f"Знайдено: <strong>{self.user1.username}</strong> (ID {self.user1.id})")