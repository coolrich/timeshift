from logging import getLogger

import pytest
from django.contrib.auth import get_user_model
from ninja.testing import TestClient

# import django_project.api as api  # import user_router
from accounts.models import ThrottleRule
from tests.utils.utils import get_current_method_path

logger = getLogger(__name__)

User = get_user_model()

class TestUserAPITests:

    @pytest.fixture(autouse=True)
    def setup(self, user, request):
        from ninja import NinjaAPI
        from core.auth import SessionOrToken
        from core.api.throttles import GlobalUserThrottle
        api = NinjaAPI(auth=SessionOrToken(),
                       version="test",
                       throttle=GlobalUserThrottle()
                       )
        from accounts.api.api import create_user_router
        request.cls.router = create_user_router()
        api.add_router("/user/", router=request.cls.router)
        # api.exception_handler = create_exception_handler(api)
        self.user = user
        request.cls.api = api
        self.client = TestClient(api)


    def test_update_token(self):
        old_token = self.user.api_token
        logger.debug(f"test_update_token(): old_token: {old_token}")
        payload = {"refresh_token": True}
        response = self.client.put("/user/update/", json=payload,
                                   headers={"Authorization": f"Bearer {self.user.api_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["api_token"] != old_token
        self.user.refresh_from_db()
        assert self.user.api_token != old_token

    def test_update_token_with_invalid_auth_token(self):
        payload = {"refresh_token": True}
        response = self.client.put("/user/update/", json=payload, headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401
        data = response.json()
        logger.debug(f"test_update_token_with_invalid_auth_token(): data: {data}")
        assert data["detail"] == "Invalid authentication token"

    def test_throttle(self, free_plan):
        limit = free_plan.throttle_rules.get(scope=ThrottleRule.Scope.GLOBAL).max_requests
        logger.debug(f"{get_current_method_path(self, self.test_throttle)}: request limit: {limit}")
        for i in range(limit):
            response = self.client.put("/user/update/",
                                       headers={"Authorization": f"Bearer {self.user.api_token}"},
                                       json={"refresh_token": True})
            logger.debug(f"{get_current_method_path(self, self.test_throttle)}: response: {response.json()}")
            assert response.status_code == 200
            self.user.refresh_from_db()
        old_token = self.user.api_token
        response = self.client.put("/user/update/",
                                   headers={"Authorization": f"Bearer {self.user.api_token}"},
                                   json={"refresh_token": True})
        logger.debug(f"{get_current_method_path(self, self.test_throttle)}: response: {response.json()}")
        self.user.refresh_from_db()
        assert old_token == self.user.api_token
        assert response.status_code == 429, f"Expected 429, got {response.status_code}"
        data = response.json()
        logger.debug(f"test_throttle(): data: {data}")
        assert data["detail"] == "Too many requests."
