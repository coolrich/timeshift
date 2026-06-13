from logging import getLogger
from time import time
from unittest.mock import MagicMock

import pytest
from django.core.cache import cache

from accounts.exceptions import LimitExceeded
from accounts.models import ThrottleRule
from accounts.services.rate_limit import RateLimitService

logger = getLogger(__name__)

@pytest.mark.django_db(transaction=True)
class TestRateLimitService:

    @pytest.fixture(autouse=True)
    def setup(self, users_factory_sync, user, auth_client):
        cache.clear()
        logger.debug(f"tests.accounts.services.test_ratelimit_service.TestRateLimitService.setup():")
        self.user = user
        self.scope = ThrottleRule.Scope.GLOBAL
        self.request = MagicMock(auth=self.user)
        yield
        cache.clear()

    def test_enforce_request_success(self):
        try:
            RateLimitService.enforce_request(self.request, self.scope)
        except LimitExceeded:
            assert False, "LimitExceeded shouldn't have happened."

    def test_enforce_request_failure(self):
        RateLimitService.enforce_request(self.request, self.scope)
        key = RateLimitService.get_cache_key(self.request, self.scope)
        history = cache.get(key)
        now = time()
        history.extend([now,now,now,now,now,now,])
        duration = 60
        cache.set(key, history, duration)
        logger.debug(f"tests.accounts.services.test_ratelimit_service.TestRateLimitService."
                     f"test_enforce_request_failure(): user.rates: {self.user.rates_cache}")
        with pytest.raises(LimitExceeded):
            RateLimitService.enforce_request(self.request, self.scope)


