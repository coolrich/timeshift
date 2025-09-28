from django.test import TestCase

class TestAccounts(TestCase):
    def test_login(self):
        self.client.login(username='testuser', password='testpass')
        self.assertTrue(self.client.is_authenticated)
        self.assertEqual(self.client.session.get('_auth_user_id'), 1)
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')

        self.client.logout()
        self.assertFalse(self.client.is_authenticated)
        self.assertEqual(self.client.session.get('_auth_user_id'), None)

    def test_logout(self):
        self.client.login(username='testuser', password='testpass')
        self.client.logout()
        self.assertFalse(self.client.is_authenticated)
        self.assertEqual(self.client.session.get('_auth_user_id'), None)

class TestUsers(TestCase):
    def test_create_user(self):
        self.client.post('/accounts/signup/', {'username': 'testuser', 'password1': 'testpass', 'password2': 'testpass'})
        self.assertTrue(self.client.is_authenticated)
        self.assertEqual(self.client.session.get('_auth_user_id'), 1)
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')

        self.client.logout()
        self.assertFalse(self.client.is_authenticated)
        self.assertEqual(self.client.session.get('_auth_user_id'), None)

    def test_update_user(self):
        self.client.login(username='testuser', password='testpass')
        self.client.post('/accounts/update/', {'username': 'testuser', 'password1': 'testpass', 'password2': 'testpass'})
        self.assertTrue(self.client.is_authenticated)
        self.assertEqual(self.client.session.get('_auth_user_id'), 1)
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')

        self.client.logout()
        self.assertFalse(self.client.is_authenticated)
        self.assertEqual(self.client.session.get('_auth_user_id'), None)

    def test_delete_user(self):
        self.client.login(username='testuser', password='testpass')
        self.client.post('/accounts/delete/', {'username': 'testuser', 'password1': 'testpass', 'password2': 'testpass'})
        self.assertFalse(self.client.is_authenticated)
        self.assertEqual(self.client.session.get('_auth_user_id'), None)
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.session.get('_auth_user_backend'), 'django.contrib.auth.backends.ModelBackend')
