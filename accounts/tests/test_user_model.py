from django.test import TestCase
from django.contrib.auth import get_user_model
from logging import getLogger

from django.urls import reverse

User = get_user_model()
logger = getLogger(__name__)

class UserModelTests(TestCase):

    def test_create_user(self):
        User.objects.create(username="John", password="123SuperSecret!")
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get(username="John").password, "123SuperSecret!")
        self.assertTrue(User.objects.filter(username="John").exists())

    def test_create_user_with_fullname(self):
        User.objects.create(username="John", full_name="John Doe")
        self.assertTrue(User.objects.filter(full_name="John Doe").exists())



