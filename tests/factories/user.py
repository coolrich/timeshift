# accounts/factories/user.py

from django.contrib.auth import get_user_model
from accounts.models import UserSubscription
from logging import getLogger

logger = getLogger(__name__)

User = get_user_model()


class UserFactory:
    @staticmethod
    def create(**kwargs):
        defaults = {
            'username': "emily11",
            'password': "emilypass",
            'email': "emily1@example.com",
            'phone_number': "+380969817232",
            'max_clocks_count': 10
        }
        defaults.update(kwargs)

        password = defaults.pop("password")

        user = User.objects.create_user(password=password, **defaults)

        logger.debug(f"UserFactory.create: users credentials: {defaults}")
        return user

    @staticmethod
    def with_plan(plan, **kwargs):

        user = UserFactory.create(**kwargs)

        us, _ = UserSubscription.objects.get_or_create(
            user=user,
            plan=plan
        )

        return user
