from django.core.cache import cache
from logging import getLogger
from accounts.models import ThrottleRule

logger = getLogger(__name__)

CACHE_TTL = 300


def build_user_rates(user) -> dict:
    cache_key = f"user_rates:{user.id}:v{user.rates_version}"

    cached = cache.get(cache_key)
    if cached:
        return cached
    rules = ThrottleRule.objects.filter(plan=user.subscription.plan)
    rates = {rule.scope: rule.rate for rule in rules}
    logger.debug(f"core.api.throttles.build_user_rates(): rates: {rates}")
    user_rates = user.rates or {}
    logger.debug(f"core.api.throttles.build_user_rates(): user_rates: {user_rates}")
    for scope, config in user_rates.items():
        if not isinstance(config, dict):
            continue

        rate = config.get("rate")
        if rate:
            rates[scope] = rate

    cache.set(cache_key, rates, CACHE_TTL)

    return rates
