# accounts/signals.py
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F

from accounts.models import ThrottleRule
from logging import getLogger

logger = getLogger(__name__)

User = get_user_model()

@receiver([post_save, post_delete], sender=ThrottleRule)
def invalidate_user_rates_cache(sender, instance, **kwargs):
    logger.debug(f"Invalidating user rates cache for {instance}")

    user_id = getattr(instance, "user_id", None)
    plan_id = getattr(instance, "plan_id", None)

    # user-specific rule
    if user_id:
        User.objects.filter(id=user_id).update(
            rates_version=F("rates_version") + 1
        )
        return

    # plan-level rule
    if plan_id:
        User.objects.filter(
            subscription__plan_id=plan_id
        ).update(
            rates_version=F("rates_version") + 1
        )