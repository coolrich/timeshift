from http.client import responses

from django.test import TestCase
from django.contrib.auth import get_user_model
from ninja.testing import TestClient
from core.api import router
from core.models import VirtualClock

User = get_user_model()
client = TestClient(router)


class ClockTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily")

    def test_create_clock_with_payload(self):
        payload = {"name": "MyClock"}

        response = client.post(
            path='/clocks/',
            json=payload,
            headers={'Authorization': f"Bearer {self.user.api_token}"}
        )

        # Перевірка статусу
        self.assertEqual(response.status_code, 201)

        # Перевірка даних відповіді
        data = response.json()
        self.assertEqual(data["name"], "MyClock")
        self.assertIn("id", data)

        # Перевірка БД
        clock = VirtualClock.objects.get(id=data["id"])
        self.assertEqual(clock.user_owner, self.user)
        self.assertEqual(clock.name, "MyClock")

    def test_create_clock_without_payload(self):
        response = client.post(
            path='/clocks/',
            headers={'Authorization': f"Bearer {self.user.api_token}"}
        )

        # Тут залежить від логіки ендпоінта:
        # Якщо ендпоінт повинен створювати clock без name:
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsNone(data["name"])
        self.assertIn("id", data)

        # Перевірка БД
        clock = VirtualClock.objects.get(id=data["id"])
        self.assertEqual(clock.user_owner, self.user)
        self.assertIsNone(clock.name)


    def test_retrieve_clock(self):
        user = self.user
        clock = VirtualClock.objects.create(user_owner=user, name="TestClock")

        response = client.get(f"/clocks/{clock.id}/", headers={"Authorization": f"bearer {str(user.api_token)}"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "TestClock")
        self.assertEqual(data["user_owner_id"], user.id)

    def test_list_clocks(self):
        user = self.user
        VirtualClock.objects.create(user_owner=user, name="Clock A")
        VirtualClock.objects.create(user_owner=user, name="Clock B")

        response = client.get("/clocks/", headers={"Authorization": f"bearer {str(user.api_token)}"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        names = [c["name"] for c in data]
        self.assertSetEqual(set(names), {"Clock A", "Clock B"})

    def test_update_clock_name_and_tick(self):
        user = self.user
        clock = VirtualClock.objects.create(user_owner=user, name="Old Name", tick_enabled=False)
        payload = {
            "id": clock.id,
            "name": "New Name",
            "tick_enabled": True,
        }

        response = client.put("/clocks/", json=payload, headers={"Authorization": f"bearer {str(user.api_token)}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("name", data["changed_fields"])
        self.assertEqual(data["name"], "New Name")

        clock.refresh_from_db()
        self.assertEqual(clock.name, "New Name")
        self.assertTrue(clock.tick_enabled)

    def test_update_clock_denied_for_non_owner(self):
        owner = self.user
        stranger = User.objects.create_user(username="nick")
        clock = VirtualClock.objects.create(user_owner=owner, name="Clock1")

        payload = {"id": clock.id, "allowed_users": [str(stranger.id)]}
        response = client.put("/clocks/", json=payload,
                              headers={"Authorization": f"Bearer {str(stranger.api_token)}"})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Permission denied")

    def test_clock_not_found_for_id(self):
        user = self.user
        clock = VirtualClock.objects.create(user_owner=user, name="Clock1")

        clock_id = int(clock.id) + 1
        response = client.get(f"/clocks/{clock_id}/", headers={"Authorization": f"bearer {str(user.api_token)}"})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Not found")
