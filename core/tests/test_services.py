from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone as dj_timezone

from core.models import VirtualClock
from core.services import VirtualClockController
from freezegun import freeze_time

User = get_user_model()


@freeze_time("2025-10-31 15:15:30")
class TestVirtualClockController(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.clock = VirtualClock.objects.create(user_owner=self.user)
        self.controller = VirtualClockController(self.clock)

    def test_get_time(self):
        """
        Перевіряємо, що get_time() повертає точний UTC час
        та його локальну конвертацію можна отримати в Києві.
        """
        time_iso = self.controller.get_time()
        time_utc = datetime.fromisoformat(time_iso)  # aware datetime у UTC
        self.assertEqual(time_utc, dj_timezone.now())

        # Перевіряємо конвертацію в Київ
        time_kyiv = time_utc.astimezone(ZoneInfo("Europe/Kyiv"))
        expected_kyiv = dj_timezone.now().astimezone(ZoneInfo("Europe/Kyiv"))
        self.assertEqual(time_kyiv, expected_kyiv)

    def test_get_user_owner(self):
        """
        Перевіряємо, що контролер повертає правильного власника.
        """
        self.assertEqual(self.controller.get_user_owner(), self.user)

    def test_set_time(self):
        """
        Перевіряємо, що можна вручну встановити час.
        """
        manual_time = datetime(2025, 10, 31, 16, 15, 30, tzinfo=timezone.utc)
        self.controller.set_time(manual_time)

        time_iso = self.controller.get_time()
        time_dt = datetime.fromisoformat(time_iso)
        self.assertEqual(time_dt, manual_time)

    def test_set_real_time(self):
        """
        Перевіряємо, що set_real_time() встановлює поточний (заморожений) час
        та вимикає tick.
        """
        updated_clock = self.controller.set_real_time()
        time_dt = datetime.fromisoformat(self.controller.get_time())
        expected_time = dj_timezone.now()

        # Перевірка часу
        self.assertEqual(time_dt, expected_time)

        # Перевірка, що tick вимкнено
        self.assertFalse(updated_clock.tick_enabled)

    def test_toggle_tick(self):
        """
        Перевіряємо, що toggle_tick():
        1) перемикає стан tick, якщо enabled=None
        2) встановлює стан tick, якщо передано enabled=True/False
        3) оновлює last_updated і current_time
        """
        # Початковий стан tick
        initial_tick = self.controller.virtual_clock.tick_enabled

        # 1️⃣ toggle без аргументів
        updated_clock = self.controller.toggle_tick()
        self.assertEqual(updated_clock.tick_enabled, not initial_tick)
        self.assertEqual(updated_clock.last_updated, dj_timezone.now())
        self.assertEqual(updated_clock.current_time, self.controller._current_time())

        # 2️⃣ явне встановлення tick=True
        updated_clock = self.controller.toggle_tick(enabled=True)
        self.assertTrue(updated_clock.tick_enabled)
        self.assertEqual(updated_clock.last_updated, dj_timezone.now())
        self.assertEqual(updated_clock.current_time, self.controller._current_time())

        # 3️⃣ явне встановлення tick=False
        updated_clock = self.controller.toggle_tick(enabled=False)
        self.assertFalse(updated_clock.tick_enabled)
        self.assertEqual(updated_clock.last_updated, dj_timezone.now())
        self.assertEqual(updated_clock.current_time, self.controller._current_time())
