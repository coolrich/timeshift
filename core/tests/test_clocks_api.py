import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from ninja.testing import TestClient

from core.api import router
from core.models import VirtualClock

User = get_user_model()
client = TestClient(router)
logger = logging.getLogger(__name__)

class ClockTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily",
                                             password="emilypass",
                                             email="emily@example.com",
                                             phone_number="+380969817231",
                                             max_clocks_count=10)
        # self.clock = VirtualClock.objects.create(user_owner=self.user, name="TestClock1")

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

    def test_speed_min_max_vals(self):
        self.clock = VirtualClock.objects.create(user_owner=self.user, name="TestClock")
        validators = self.clock._meta.get_field("speed").validators
        logger.debug(f"core.tests.test_clocks_api.py: test_speed_min_max_vals(): min_validator: "
                     f"{validators[0].limit_value}")
        logger.debug(f"core.tests.test_clocks_api.py: test_speed_min_max_vals(): max_validator: "
                     f"{validators[1].limit_value}")
        self.assertEqual(validators[0].limit_value, 0.01)
        self.assertEqual(validators[1].limit_value, 100.0)

    def test_update_clock_name_tick_speed(self):
        user = self.user
        clock = VirtualClock.objects.create(user_owner=user, name="Old Name", tick_enabled=False)
        payload = {
            "clock_id": clock.id,
            "name": "New Name",
            "tick_enabled": True,
            "speed": 2
        }

        response = client.put("/clocks/", json=payload, headers={"Authorization": f"bearer {str(user.api_token)}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("name", data["changed_fields"])
        self.assertEqual(data["name"], "New Name")

        clock.refresh_from_db()
        self.assertEqual(clock.name, "New Name")
        self.assertTrue(clock.tick_enabled)
        self.assertEqual(clock.speed, 2)

    def test_update_clock_nonvalid_speed(self):
        clock = VirtualClock.objects.create(user_owner=self.user, name="TestClock")
        validators = clock._meta.get_field("speed").validators
        with self.assertRaises(ValidationError):
            response = client.put("/clocks/", json={"clock_id": clock.id, "speed": validators[1].limit_value + 1},
                                  headers={"Authorization": f"bearer {str(self.user.api_token)}"})
            logger.debug(f"core.tests.test_clocks_api.py: test_update_clock_nonvalid_speed(): response: {response}")
            response.raise_for_status()

    def test_update_clock_denied_for_non_owner(self):
        owner = self.user
        stranger = User.objects.create_user(username="nick",
                                            password="nickpass",
                                            email="nick@example.com",
                                            phone_number="+380969817231"
                                            )
        clock = VirtualClock.objects.create(user_owner=owner, name="Clock1")

        payload = {"clock_id": clock.id,
                   "allowed_users": [str(stranger.id)]}
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

    def test_delete_clock_for_owner(self):
        user = self.user
        clock = VirtualClock.objects.create(user_owner=user, name="Clock1")
        response = client.delete(f"/clocks/{clock.id}/", headers={"Authorization": f"bearer {str(user.api_token)}"})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(VirtualClock.objects.count(), 0)

    def test_delete_clock_for_non_owner(self):
        user = User.objects.create_user(username="nick",
                                  password="nickpass",
                                  email="nick@example.com",
                                  phone_number="+380969817231"
                                  )
        clock = VirtualClock.objects.create(user_owner=self.user, name="Clock1")
        response = client.delete(f"/clocks/{clock.id}/", headers={"Authorization": f"bearer {str(user.api_token)}"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(VirtualClock.objects.count(), 1)
