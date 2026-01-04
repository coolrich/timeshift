from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from logging import getLogger

from core.models import VirtualClock

logger = getLogger(__name__)
User = get_user_model()

class ClockTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily",
                                             password="emilypass",
                                             email="emily@example.com",
                                             phone_number="+380969817231",
                                             max_clocks_count=1)
        self.clock = VirtualClock.objects.create(user_owner=self.user)

    def test_users_clocks_limit(self):
        with self.assertRaises(IntegrityError):
            self.clock = VirtualClock.objects.create(user_owner=self.user)
        logger.debug(f"ClockTests.test_users_clock_limit(): len(self.user.virtual_clocks): {self.user.virtual_clocks.count()}")
        self.assertEqual(self.user.virtual_clocks.count(), 1)