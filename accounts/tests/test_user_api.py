from logging import getLogger

from django.contrib.auth import get_user_model
from django.test import TestCase
# from ninja import NinjaAPI
from ninja.testing import TestClient

# import accounts.api.api as api
# from django_project.api import api as ninja_api
from django_project.api import user_router

logger = getLogger(__name__)

User = get_user_model()

# def get_router_by_prefix(api_instance: NinjaAPI, prefix: str):
#     for path_prefix, r in api_instance._routers:
#         if path_prefix == prefix:
#             return r
#     return None
#
# router = get_router_by_prefix(ninja_api, "/user/")
# router = api.create_user_router()
client = TestClient(user_router)


class UserAPITests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="emily",
                                             password="emilypass",
                                             email="emily@example.com",
                                             phone_number="+380969817231")

    def test_update_token(self):
        old_token = self.user.api_token
        logger.info(f"test_update_token(): old_token: {old_token}")
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
