from logging import getLogger

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from accounts.services.subscription import SubscriptionService
from accounts.services.throttle_helper import build_user_rates
from core.models import VirtualClock
from core.services import VirtualClockController

logger = getLogger(__name__)

User = get_user_model()

@pytest.mark.django_db(transaction=True)
class TestSubscriptionService:

    @pytest.fixture(autouse=True)
    def setup(self, users_factory_sync):
        self.user: User = users_factory_sync(1, 10)[0]
        logger.debug(f"tests.accounts.services.test_subscription_service.TestSubscriptionService.setup():"
                     f"self.user type:{type(self.user)}")
        self.clock = VirtualClock.objects.create(user_owner=self.user)
        self.controller = VirtualClockController(self.clock)
        # self.client = client
        # logged_in = client.login(username=self.user.username, password=USER_TEST_PASSWORD)
        # assert logged_in, "Login failed!"

    def test_invalidates_cache(self, pro_plan):
        user = self.user
        user.rates_cache = build_user_rates(user)
        new_plan = pro_plan
        cache_key = f"user_rates:{user.id}:v{user.rates_version}"
        def get(c_key):
            plan = user.subscription.plan
            rv = user.rates_version
            acache = cache.get(c_key)
            return plan, rv, acache
        plan, rv, acache = get(cache_key)
        logger.debug(f"tests.accounts.services.test_subscription_service.TestSubscriptionService."
                     f"test_invalidates_cache(): old plan:{plan}, "
                     f"user.rates_version:{rv}, "
                     f"cache before:{acache}")
        assert plan.name == 'Free'
        assert rv == 1
        assert acache
        SubscriptionService.change_user_plan(user, new_plan)
        new_plan, new_rv, new_cache = get(cache_key)
        logger.debug(f"tests.accounts.services.test_subscription_service.TestSubscriptionService."
                     f"test_invalidates_cache(): new plan:{new_plan}, "
                     f"new user.rates_version:{new_rv}, "
                     f"cache after:{new_cache}")
        assert new_plan != plan
        assert new_rv == 2
        assert new_cache is None
