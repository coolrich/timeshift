import asyncio
import logging

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction
from ninja import NinjaAPI
from ninja.testing import TestAsyncClient

from core.auth import SessionOrToken
from core.exception_handlers import create_exception_handler
from core.models import VirtualClock
from django_project.api import create_clock_router

User = get_user_model()
logger = logging.getLogger(__name__)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestClockAsyncAPI:
    """Клас для асинхронних тестів годинників"""

    @pytest.fixture(scope="class", autouse=True)
    def init_api(self, request):
        api = NinjaAPI(auth=SessionOrToken(), version="test")
        request.cls.router = create_clock_router()
        api.add_router("/clocks/", router=request.cls.router)
        api.exception_handler = create_exception_handler(api)

        request.cls.api = api
        request.cls.client = TestAsyncClient(api)

    @pytest.fixture(autouse=True)
    async def setup(self, db):
        self.user = await User.objects.acreate_user(
            username="emily",
            password="emilypass",
            email="emily@example.com",
            phone_number="+380969817231",
            max_clocks_count=8
        )

        self.stranger_user = await User.objects.acreate_user(
            username="strangeruser",
            password="testpass",
            email="strangeruser@example.com",
            phone_number="+380969817210",
            max_clocks_count=10
        )

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
        await asyncio.sleep(0)
        self.auth_headers = {
            "Authorization": f"Bearer {self.user.api_token}"
        }
        self.stranger_auth_headers = {
            "Authorization": f"Bearer {self.stranger_user.api_token}"
        }
        # await self.clock1.allowed_users.aadd(self.stranger_user.id)
        # logger.debug(f"core.TestClockAsyncAPI.setup():"
        #              f"clock1.allowed_users: {self.clock1.allowed_users}")
        yield
        # cleanup не потрібен

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
        stranger = await User.objects.acreate_user(
            username="nick",
            password="nickpass",
            email="nick@example.com",
            phone_number="+380969817231"
        )

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
            headers={"Authorization": f"Bearer {stranger.api_token}"}
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
        stranger = await User.objects.acreate_user(
            username="nick2",
            password="nickpass",
            email="nick2@example.com",
            phone_number="+380969817232"
        )

        clock = await VirtualClock.objects.acreate(
            user_owner=self.user,
            name="Clock1"
        )

        response = await self.client.delete(
            f"/clocks/{self.clock1.id}",
            headers={"Authorization": f"Bearer {stranger.api_token}"}
        )

        assert response.status_code == 404
        assert await VirtualClock.objects.filter(id=clock.id).aexists()

    @pytest.mark.django_db(transaction=True)  # transaction=True важливо для select_for_update
    async def test_clocks_race_condition(self):
        USERS_COUNT = 30
        REQUESTS_COUNT = USERS_COUNT
        start = asyncio.Event()
        another_users = [await User.objects.acreate_user(
            username=f"user{i}",
            password="userpass123",
            max_clocks_count=REQUESTS_COUNT) for i in range(USERS_COUNT)]

        async def create_clock(user: User):
            await start.wait()
            await asyncio.sleep(0.01)
            return await self.client.post(
                path='/clocks/',
                headers={
                    "Authorization": f"Bearer {user.api_token}"
                }
            )

        # tasks = [asyncio.create_task(create_clock()) for _ in range(REQUESTS_COUNT)]
        tasks = []
        for user in another_users:
            for _ in range(REQUESTS_COUNT):
                tasks.append(asyncio.create_task(create_clock(user)))
        start.set()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                raise r

        for result in results:
            if hasattr(result, "status_code"):
                logger.debug(f"Result: {result.status_code}")
            else:
                logger.error(f"Unexpected result: {result!r}")

        # --- Перевірка ---
        # clocks = VirtualClock.objects.filter(user_owner=self.stranger_user)
        for user in another_users:
            count = await VirtualClock.objects.filter(user_owner=user).acount()
            assert count == user.max_clocks_count, \
                f"Ліміт порушено для {user.username}: {count}"

        # Всі відповіді після досягнення ліміту повинні бути помилкою
        success_responses = [r for r in results if getattr(r, "status_code", None) == 201]
        error_responses = [r for r in results if getattr(r, "status_code", None) == 429]

        assert len(success_responses) == len(another_users) * another_users[0].max_clocks_count, "Невірна кількість створених годинників"
        assert len(error_responses) == len(tasks) - len(another_users) * another_users[0].max_clocks_count, "Невірна кількість помилок"
