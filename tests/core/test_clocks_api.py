import asyncio
import logging

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from ninja import NinjaAPI
from ninja.testing import TestAsyncClient

from accounts.models import ThrottleRule
from core.api.api import create_clock_router
from core.api.throttles import GlobalUserThrottle
from core.auth import SessionOrToken
from core.exception_handlers import create_exception_handler
from core.models import VirtualClock

User = get_user_model()
logger = logging.getLogger(__name__)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestClockAsyncAPI:
    """Клас для асинхронних тестів годинників"""

    @pytest.fixture(scope="class", autouse=True)
    def init_api(self, request):
        logger.debug(f"core.TestClockAsyncAPI.init_api(): start")
        api = NinjaAPI(auth=SessionOrToken(),
                       version="test",
                       throttle=GlobalUserThrottle()
                       )
        request.cls.router = create_clock_router()
        api.add_router("/clocks/", router=request.cls.router)
        api.exception_handler = create_exception_handler(api)

        request.cls.api = api
        request.cls.client = TestAsyncClient(api)
        logger.debug(f"core.TestClockAsyncAPI.init_api(): finish")

    @pytest.fixture(autouse=True)
    async def setup(self, db, users_async):
        logger.debug("core.TestClockAsyncAPI.setup(): start")

        cache.clear()

        self.user, self.stranger_user = users_async

        self.clock1 = await VirtualClock.objects.acreate(
            user_owner=self.user,
            name="Old Name",
            # allowed_users=[self.stranger_user],
            tick_enabled=False,
            speed=1.0
        )
        self.clock2 = await VirtualClock.objects.acreate(
            user_owner=self.user,
            name="Clock A",
            tick_enabled=True,
            speed=1.0
        )
        self.clock3 = await VirtualClock.objects.acreate(
            user_owner=self.user,
            name="Clock B",
            tick_enabled=True,
            speed=2.0
        )
        # await asyncio.sleep(0)
        self.auth_headers = {
            "Authorization": f"Bearer {self.user.api_token}"
        }
        self.stranger_auth_headers = {
            "Authorization": f"Bearer {self.stranger_user.api_token}"
        }
        logger.debug(f"core.TestClockAsyncAPI.init_api(): finish")
        yield

    async def test_set_real_time_for_owner(self):
        response = await self.client.post(
            "/clocks/setreal",
            json={"clock_id": self.clock1.id},
            headers=self.auth_headers
        )
        payload = response.json()
        expected = {'status', 'data', 'message'}
        assert expected == set(payload), f"Expected keys {expected}, got {set(payload)}"
        assert response.status_code == 200
        await self.clock1.arefresh_from_db()
        assert self.clock1.tick_enabled is False

    async def test_set_real_time_for_non_owner(self):
        # 1. Додаємо stranger_user у allowed_users через ORM
        clock = await VirtualClock.objects.aget(id=self.clock1.id)
        await clock.allowed_users.aadd(self.stranger_user)

        # 2. stranger_user викликає setreal
        response = await self.client.post(
            "/clocks/setreal",
            json={"clock_id": clock.id},
            headers={"Authorization": f"Bearer {self.stranger_user.api_token}"},
        )

        # 3. Перевірка відповіді API
        payload = response.json()
        expected_keys = {"status", "data", "message"}
        assert response.status_code == 200
        assert payload["status"] == "success"
        assert set(payload) == expected_keys

        # 4. Перевірка, що tick_enabled НЕ змінився
        clock_fresh = await VirtualClock.objects.aget(id=clock.id)
        assert clock_fresh.tick_enabled is False

    async def test_create_clock_with_payload(self):
        response = await self.client.post(
            "/clocks/",
            json={"name": "MyClock"},
            headers=self.auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "MyClock"
        assert "id" in data

    async def test_create_clock_without_payload(self):
        response = await self.client.post(
            path='/clocks/',
            headers=self.auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] is None
        assert "id" in data
        clock = await VirtualClock.objects.select_related("user_owner").aget(id=data["id"])
        assert clock.user_owner == self.user

    async def test_retrieve_clock(self):
        response = await self.client.get(
            f"/clocks/{self.clock1.id}",
            headers=self.auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Old Name"
        assert data["user_owner_id"] == self.user.id

    async def test_list_clocks(self):
        response = await self.client.get(
            # reverse("api-1.0.0:api-list-clocks"),
            "/clocks/",
            headers=self.auth_headers
        )

        assert response.status_code == 200
        assert len(response.json()) == 3

    async def test_update_clock_name_tick_speed(self):
        clock = await VirtualClock.objects.acreate(
            user_owner=self.user,
            name="Old Name",
            tick_enabled=False,
            speed=1.0
        )

        response = await self.client.put(
            "/clocks/",
            json={
                "clock_id": clock.id,
                "name": "New Name",
                "tick_enabled": True,
                "speed": 2
            },
            headers=self.auth_headers
        )

        assert response.status_code == 200
        await clock.arefresh_from_db()
        assert clock.name == "New Name"
        assert clock.tick_enabled is True
        assert clock.speed == 2

    async def test_update_clock_nonvalid_speed(self):
        validators = self.clock1._meta.get_field("speed").validators

        response = await self.client.put(
            "/clocks/",
            json={
                "clock_id": self.clock1.id,
                "speed": validators[1].limit_value + 1
            },
            headers=self.auth_headers
        )

        assert response.status_code == 422

    async def test_update_clock_denied_for_non_owner(self):
        stranger = self.stranger_user

        clock = await VirtualClock.objects.acreate(
            user_owner=self.user,
            name="Clock1"
        )

        response = await self.client.put(
            "/clocks/",
            json={
                "clock_id": clock.id,
                "allowed_users": [str(stranger.id)]
            },
            headers={"Authorization": f"Bearer {stranger.api_token}"},
            user=stranger
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"

    async def test_clock_not_found_for_id(self):
        response = await self.client.get(
            "/clocks/999999",
            headers=self.auth_headers
        )

        assert response.status_code == 404

    async def test_delete_clock_for_owner(self):
        clock = await VirtualClock.objects.acreate(
            user_owner=self.user,
            name="Clock1"
        )

        response = await self.client.delete(
            f"/clocks/{clock.id}",
            headers=self.auth_headers
        )

        assert response.status_code == 204
        assert not await VirtualClock.objects.filter(id=clock.id).aexists()

    async def test_delete_clock_for_non_owner(self):
        stranger = self.stranger_user

        response = await self.client.delete(
            f"/clocks/{self.clock1.id}",
            headers={"Authorization": f"Bearer {stranger.api_token}"},
            # user=stranger
        )

        assert response.status_code == 404

    @pytest.mark.django_db(transaction=True)
    async def test_clocks_race_condition(self, users_factory_async, free_plan):

        USERS_COUNT = 5
        REQUESTS_COUNT = USERS_COUNT

        start = asyncio.Event()
        users = await users_factory_async(USERS_COUNT, REQUESTS_COUNT, free_plan)

        async def create_clock(user):
            await start.wait()
            return await self.client.post(
                path='/clocks/',
                headers={"Authorization": f"Bearer {user.api_token}"}
            )

        tasks = [
            asyncio.create_task(create_clock(user))
            for user in users
            for _ in range(REQUESTS_COUNT)
        ]

        start.set()
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            assert not isinstance(r, Exception), r
            assert hasattr(r, "status_code"), r

        max_count = (
            await ThrottleRule.objects
            .filter(scope=ThrottleRule.Scope.CLOCKS_CREATE)
            .afirst()
        ).max_requests

        for user in users:
            count = await user.virtual_clocks.acount()
            assert count == max_count, f"{user.username}: {count}"

        success = [r for r in results if r.status_code == 201]
        errors = [r for r in results if r.status_code == 429]

        expected_success = USERS_COUNT * max_count

        assert len(success) == expected_success
        assert len(errors) == len(tasks) - expected_success

    async def test_clock_throttle_success(self):
        response = None
        requests_limit = (
            await ThrottleRule.objects
            .filter(scope=ThrottleRule.Scope.GLOBAL)
            .afirst()
        ).max_requests
        logger.debug(f"tests.core.test_clocks_api.TestClockAsyncAPI.test_clock_throttling_success():"
                     f"requests_limit: {requests_limit}")
        for _ in range(requests_limit):
            response = await self.client.get(
                f"/clocks/{self.clock1.id}",
                headers=self.auth_headers
            )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Old Name"
        assert data["user_owner_id"] == self.user.id

    async def test_clock_throttle_fail(self, users_factory_async):
        clock = await VirtualClock.objects.acreate(
            user_owner=self.user
        )
        request_limit = (
            await self.user.subscription.plan.throttle_rules.aget(scope=ThrottleRule.Scope.GLOBAL)).max_requests
        for _ in range(request_limit):
            response = await self.client.get(
                f"/clocks/{clock.id}",
                headers=self.auth_headers
            )
            assert response.status_code == 200
        response = await self.client.get(
            f"/clocks/{clock.id}",
            headers=self.auth_headers
        )
        assert response.status_code == 429
        data = response.json()
        # logger.debug(f"core.accounts.test_clocks_api.TestClockAsyncAPI.test_clock_throttling_fail: response: {data}")
        assert data["detail"] == "Too many requests."

    async def test_create_clock_throttle_success(self):
        request_limit = (
            await self.user.subscription.plan.throttle_rules.aget(scope=ThrottleRule.Scope.CLOCKS_CREATE)).max_requests
        for _ in range(request_limit):
            response = await self.client.post(
                path='/clocks/',
                headers=self.auth_headers
            )
            assert response.status_code == 201
        logger.debug(f"core.tests.test_clocks_api.TestClockAsyncAPI.test_create_clock_throttle(): response: {response}")
        assert response.status_code == 201
        data = response.json()
        assert data["name"] is None
        assert "id" in data
        clock = await VirtualClock.objects.select_related("user_owner").aget(id=data["id"])
        assert clock.user_owner == self.user

    async def test_create_clock_throttle_fail(self, user):
        # робимо запити до ліміту
        request_limit = (
            await self.user.subscription.plan.throttle_rules.aget(scope=ThrottleRule.Scope.CLOCKS_CREATE)).max_requests
        for _ in range(request_limit):
            r = await self.client.post(
                path='/clocks/',
                headers={"Authorization": f"Bearer {self.user.api_token}"},
            )
            assert r.status_code == 201

        # наступний запит має впасти
        r = await self.client.post(
            path='/clocks/',
            headers={"Authorization": f"Bearer {self.user.api_token}"},
        )

        data = r.json()

        assert r.status_code == 429
        assert data["detail"] == "Too many requests."
