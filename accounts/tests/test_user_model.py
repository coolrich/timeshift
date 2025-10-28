from django.test import TestCase
from django.contrib.auth import get_user_model
from logging import getLogger

User = get_user_model()
logger = getLogger(__name__)

class UserModelTests(TestCase):

    def test_create_user(self):
        # logger.debug("test_create_user(): begin")
        user = User.objects.create_user(username="John")
        self.assertEqual(user.username, "John")
        # logger.debug("test_create_user(): success")