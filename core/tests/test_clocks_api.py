import logging

import pytest
from django.contrib.auth import get_user_model
from ninja import NinjaAPI
from ninja.testing import TestAsyncClient

from core.auth import SessionOrToken
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
        api.add_router("/clocks/", create_clock_router())

        request.cls.api = api
        request.cls.client = TestAsyncClient(api)

    @pytest.fixture(autouse=True)
    async def setup(self, db):
        self.user = await User.objects.acreate_user(
            username="emily",
            password="emilypass",
            email="emily@example.com",
            phone_number="+380969817231",
            max_clocks_count=10
        )

        self.clock1 = await VirtualClock.objects.acreate(
            user_owner=self.user,
            name="Old Name",
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

        self.auth_headers = {
            "Authorization": f"Bearer {self.user.api_token}"
        }

        yield
        # cleanup не потрібен

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
