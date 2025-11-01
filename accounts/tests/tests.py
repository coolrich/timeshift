from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from logging import getLogger

logger = getLogger(__name__)
User = get_user_model()

class TestAccounts(TestCase):
    def test_log_in_out(self):
        User.objects.create_user(username='testuser', password='testpass')
        # logged_in = self.client.login(username='testuser', password='testpass')
        # self.assertTrue(logged_in)
        response = self.client.post(reverse("login"), {'username': 'testuser', 'password': 'testpass'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('_auth_user_id'), '1')
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
        self.assertFalse(self.client.logout())
        self.assertEqual(self.client.session.get('_auth_user_id'), None)

class TestUsers(TestCase):
    def test_create_user(self):
        response = self.client.post(reverse("signup"), {'username': 'testuser', 'password1': 'SuperSecret123!', 'password2': 'SuperSecret123!'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='testuser').exists())
        # self.assertTrue(is_authenticated)
        # self.assertEqual(self.client.session.get('_auth_user_id'), 1)
        # self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
        # self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')

    def test_create_user_with_bad_password(self):
        response = self.client.post(reverse("signup"), {"username": "John", "password1": "123", "password2": "123"})
        logger.info(f"test_create_user_with_bad_password(): {response.status_code}")
        self.assertEqual(response.status_code, 200)
#
#         self.client.logout()
#         self.assertFalse(self.client.is_authenticated)
#         self.assertEqual(self.client.session.get('_auth_user_id'), None)
#
#     def test_update_user(self):
#         self.client.login(username='testuser', password='testpass')
#         self.client.post('/accounts/update/', {'username': 'testuser', 'password1': 'testpass', 'password2': 'testpass'})
#         self.assertTrue(self.client.is_authenticated)
#         self.assertEqual(self.client.session.get('_auth_user_id'), 1)
#         self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
#         self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
#
#         self.client.logout()
#         self.assertFalse(self.client.is_authenticated)
#         self.assertEqual(self.client.session.get('_auth_user_id'), None)
#
#     def test_delete_user(self):
#         self.client.login(username='testuser', password='testpass')
#         self.client.post('/accounts/delete/', {'username': 'testuser', 'password1': 'testpass', 'password2': 'testpass'})
#         self.assertFalse(self.client.is_authenticated)
#         self.assertEqual(self.client.session.get('_auth_user_id'), None)
#         self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
#         self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
