from django.test import TestCase
from ninja.testing import TestClient
from accounts.api import router
from django.contrib.auth import get_user_model
from logging import getLogger

logger = getLogger(__name__)

User = get_user_model()
client = TestClient(router)

class UserAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily",
                                             password="emilypass",
                                             email="emily@example.com",
                                             phone_number="+380969817231")

    def test_update_token(self):
        old_token = self.user.api_token
        payload = {"refresh_token": True}
        response = client.put("/update/", json=payload, headers={"Authorization": f"Bearer {self.user.api_token}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotEqual(data["api_token"], self.user.api_token)
        self.user.refresh_from_db()
        self.assertNotEqual(old_token, self.user.api_token)

    def test_update_token_with_invalid_auth_token(self):
        payload = {"refresh_token": True}
        response = client.put("/update/", json=payload, headers={"Authorization": "Bearer invalid_token"})
        self.assertEqual(response.status_code, 401)
        data = response.json()
        logger.debug(f"test_update_token_with_invalid_auth_token(): data: {data}")
        self.assertEqual(data["detail"], "Invalid authentication token")

