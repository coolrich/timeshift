from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class TestAccounts(TestCase):
    def test_log_in_out(self):
        User.objects.create_user(username='testuser', password='testpass')
        logged_in = self.client.login(username='testuser', password='testpass')
        self.assertTrue(logged_in)
        self.assertEqual(self.client.session.get('_auth_user_id'), '1')
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
        self.assertFalse(self.client.logout())
        self.assertEqual(self.client.session.get('_auth_user_id'), None)

class TestUsers(TestCase):
    def test_create_user(self):
        response = self.client.post('/accounts/signup/', {'username': 'testuser', 'password1': 'SuperSecret123!', 'password2': 'SuperSecret123!'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='testuser').exists())
        # self.assertTrue(is_authenticated)
        # self.assertEqual(self.client.session.get('_auth_user_id'), 1)
        # self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
        # self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
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
