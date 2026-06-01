from logging import getLogger

from accounts.models import Plan, UserSubscription

logger = getLogger(__name__)


from django.db import transaction
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured


class SubscriptionService:
    """Allows it to manipulate plans and cancel user rates"""

    @staticmethod
    def assign_default_plan(user):
        """Assigns a default plan to the user"""
        with transaction.atomic():
            try:
                free_plan = Plan.objects.get(code=Plan.Code.FREE)
            except Plan.DoesNotExist:
                raise ImproperlyConfigured("Default FREE plan is missing")

            subscription, created = UserSubscription.objects.get_or_create(
                user=user,
                defaults={"plan": free_plan}
            )

            if not created and subscription.plan != free_plan:
                subscription.plan = free_plan
                subscription.save(update_fields=["plan"])

        SubscriptionService.invalidate_user_rates(user)

    @staticmethod
    def change_user_plan(user, new_plan):
        """Assigns a new plan to the user"""
        with transaction.atomic():
            try:
                subscription = user.subscription
            except UserSubscription.DoesNotExist:
                raise ImproperlyConfigured("User has no subscription")

            subscription.plan = new_plan
            subscription.save(update_fields=["plan"])

        SubscriptionService.invalidate_user_rates(user)

    @staticmethod
    def invalidate_user_rates(user):
        """
        Invalidates cache through versioning
        """
        logger.debug(f"accounts.services.subscription.SubscriptionService.invalidate_user_rates():"
                     f"before user.save() user.rates_version:{user.rates_version}")
        cache_key = f"user_rates:{user.id}:v{user.rates_version}"
        cache.delete(cache_key)
        user.rates_version += 1
        user.save(update_fields=["rates_version"])
        logger.debug(f"accounts.services.subscription.SubscriptionService.invalidate_user_rates():"
                     f"after user.save() user.rates_version:{user.rates_version}")

