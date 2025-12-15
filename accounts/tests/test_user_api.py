from django.test import TestCase
from ninja.testing import TestClient
from accounts.api import router
from django.contrib.auth import get_user_model

User = get_user_model()
client = TestClient(router)

class UserAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily",
                                             password="emilypass",
                                             email="emily@example.com",
                                             phone_number="+380969817231")

    def test_update(self):
        payload = {"refresh_token": True}
        response = client.put("/update/", json=payload, headers={"Authorization": f"Bearer {self.user.api_token}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.user.refresh_from_db()
        self.assertEqual(data["api_token"], self.user.api_token)