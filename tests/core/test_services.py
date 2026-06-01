import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone as dj_timezone
from freezegun import freeze_time

from accounts.models import TimeShiftUser
from core.models import VirtualClock
from core.services import VirtualClockController

logger = logging.getLogger(__name__)
User = get_user_model()

@pytest.mark.django_db
@freeze_time("2025-10-31 15:15:30")
class TestVirtualClockControllerSync:

    @pytest.fixture(autouse=True)
    def setup(self, users_factory_sync):
        self.user = users_factory_sync(1, 10)[0]
        self.clock = VirtualClock.objects.create(user_owner=self.user)
        self.controller = VirtualClockController(self.clock)

    def test_get_time(self):
        time_iso = self.controller.get_iso_time()
        time_utc = datetime.fromisoformat(time_iso)

        assert time_utc == dj_timezone.now()

        time_kyiv = time_utc.astimezone(ZoneInfo("Europe/Kyiv"))
        expected_kyiv = dj_timezone.now().astimezone(ZoneInfo("Europe/Kyiv"))

        assert time_kyiv == expected_kyiv

    def test_get_user_owner(self):
        assert self.controller.get_user_owner() == self.user

    def test_set_time(self):
        manual_time = datetime(2025, 10, 31, 16, 15, 30, tzinfo=timezone.utc)

        self.controller.set_time(manual_time)

        time_iso = self.controller.get_iso_time()
        time_dt = datetime.fromisoformat(time_iso)

        assert time_dt == manual_time

    def test_toggle_tick(self):
        initial_tick = self.controller.virtual_clock.tick_enabled

        updated_clock = self.controller.toggle_tick().virtual_clock
        assert updated_clock.tick_enabled is (not initial_tick)
        assert updated_clock.last_updated == dj_timezone.now()
        assert updated_clock.current_time == self.controller._current_time()

        updated_clock = self.controller.toggle_tick(enabled=True).virtual_clock
        assert updated_clock.tick_enabled is True

        updated_clock = self.controller.toggle_tick(enabled=False).virtual_clock
        assert updated_clock.tick_enabled is False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@freeze_time("2025-10-31 15:15:30")
class TestVirtualClockControllerAsync:

    @pytest.fixture(autouse=True)
    async def setup(self, users_factory_async, free_plan):
        self.user = (await users_factory_async(1, 10, free_plan))[0]

        self.clock = await sync_to_async(VirtualClock.objects.create)(
            user_owner=self.user
        )

        self.controller = VirtualClockController(self.clock)

    async def test_set_real_time(self):
        updated_clock = await self.controller.set_real_time_async()

        time_dt = datetime.fromisoformat(self.controller.get_iso_time())
        expected_time = dj_timezone.now()

        assert time_dt == expected_time
        assert updated_clock.tick_status is False

    async def test_update_allowed_users_full_update(self, users_factory_async, free_plan):
        u1, u2 = await users_factory_async(2, 10, free_plan)

        payload = {'allowed_users': [u1.id, u2.id]}

        await self.controller.update_allowed_users_async(payload)
        await self.clock.arefresh_from_db()

        allowed_users = [
            user_id async for user_id in
            self.clock.allowed_users.values_list("id", flat=True)
        ]

        assert set(allowed_users) == {u1.id, u2.id}

    async def test_update_allowed_users_add(self, users_factory_async, free_plan):
        u1, u2 = await users_factory_async(2, 10, free_plan)

        payload = {'add_users': [u1.id, u2.id]}

        await self.controller.update_allowed_users_async(payload)
        await self.clock.arefresh_from_db()

        allowed_users = [
            user_id async for user_id in
            self.clock.allowed_users.values_list("id", flat=True)
        ]

        assert set(allowed_users) == {u1.id, u2.id}

    async def test_update_allowed_users_remove(self, users_factory_async, free_plan):
        u1, u2 = await users_factory_async(2, 10, free_plan)

        users = await sync_to_async(list)(
            TimeShiftUser.objects.filter(id__in=[u1.id, u2.id])
        )

        await self.clock.allowed_users.aset(users)

        payload = {'remove_users': [u1.id, u2.id]}

        await self.controller.update_allowed_users_async(payload)

        allowed_users = [
            user_id async for user_id in
            self.clock.allowed_users.values_list("id", flat=True)
        ]

        assert allowed_users == []