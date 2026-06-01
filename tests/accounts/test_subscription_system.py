from logging import getLogger

import pytest
from django.contrib.auth import get_user_model

from accounts.models import Plan, UserSubscription
from tests.factories.plan import PlanFactory
from tests.factories.throttle import ThrottleFactory
from tests.factories.user import UserFactory

User = get_user_model()
logger = getLogger(__name__)

@pytest.mark.django_db
class TestSubscriptionSystem:
    def test_subscription_creation(self):
        user = UserFactory.create()
        defaults = {
            "code": Plan.Code.FREE,
            "name": "Free",
            "description": "Free plan",
            "is_active": True,
        }
        free_plan = PlanFactory.create(
            **defaults
        )
        ThrottleFactory.clocks_create_scope(free_plan)
        UserSubscription.objects.create(user=user, plan=Plan.objects.get(code=Plan.Code.FREE))
        subscription = User.objects.get(username=user.username).subscription
        assert subscription is not None, "Subscription not created"
        assert subscription.plan.code == Plan.Code.FREE, "Subscription plan is not free"
