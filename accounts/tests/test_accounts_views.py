from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

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
        }
        response = self.client.post(url, data)
        # перевіряємо, що редірект на profile
        self.assertRedirects(response, reverse("profile"))
        # користувач створений
        self.assertTrue(User.objects.get(username="newuser"))
        # користувач залогінений
        user = User.objects.get(username="newuser")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emily", password="verySecret123!")
        self.url = reverse("profile")

    def test_profile_requires_login(self):
        response = self.client.get(self.url)
        # редірект на login з next=
        login_url = reverse("login")
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_profile_shows_virtual_clocks(self):
        is_logged_in = self.client.login(username="emily", password="verySecret123!")
        self.assertTrue(is_logged_in)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        # у контексті є virtual_clocks
        self.assertIn("virtual_clocks", response.context)
        self.assertQuerySetEqual(
            response.context["virtual_clocks"],
            self.user.virtual_clocks.all(),
            transform=lambda x: x
        )
