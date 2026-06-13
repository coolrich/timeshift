from math import ceil
from time import time

from django.conf import settings
from django.core.cache import cache

from accounts.exceptions import LimitExceeded
from accounts.services.throttle_helper import build_user_rates
from logging import getLogger

logger = getLogger(__name__)


class RateLimitService:
    @staticmethod
    def get_request_user(request):
        """Get user"""
        return getattr(request, "auth", None) or getattr(request, "user", None)

    @staticmethod
    def get_ident(request) -> str:
        """Identifying user's ip"""
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @classmethod
    def get_cache_key(cls, request, scope: str) -> str:
        """Get cache key in form of string 'throttle:{scope}:ip:{ip}'"""
        user = cls.get_request_user(request)
        if getattr(user, "is_authenticated", False):
            return f"throttle:{scope}:user:{user.id}"
        return f"throttle:{scope}:ip:{cls.get_ident(request)}"

    @staticmethod
    def parse_rate(rate: str) -> tuple[int, int, str]:
        """Parses a string rate

           Args: rate: a string in the format requests/period

           Returns:
               tuple[int,int]
                    - num: Maximum number of allowed requests.
                    - period: Time window in seconds.
        """
        num_str, period = rate.split("/", 1)
        periods = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
        }
        num = int(num_str)
        num_period = periods[period]
        return num, num_period, period

    @classmethod
    def get_rate(cls, request, scope: str) -> str | None:
        """
        Returns the rate limit as a string in the format 'requests/period'.

        Args:
            request: Request object containing metadata about the current request.
            scope: String identifying the rate-limiting scope.

        Returns:
            str | None:
                A string in the format 'requests/period', where:
                    - requests: Maximum number of allowed requests.
                    - period: Time window in seconds.
                Returns None if no rate limit is configured.
        """
        user = cls.get_request_user(request)

        if getattr(user, "is_authenticated", False):
            rates = getattr(user, "rates_cache", None)
            if rates is None:
                rates = build_user_rates(user)
                user.rates_cache = rates

            user_rate = rates.get(scope)
            if user_rate:
                return user_rate

        fallback_rates = getattr(settings, "NINJA_THROTTLE_RATES", {})
        return fallback_rates.get(scope)

    @classmethod
    def check_request(cls, request, scope: str) -> tuple[bool, int | None, str | None]:
        """
        Returns a tuple (allowed, retry_after).

        Args:
            request: Request object containing metadata about the current request.
            scope: String identifying the rate-limiting scope.

        Returns:
            tuple[bool, int]:
                - allowed: True if the request is permitted, otherwise False.
                - retry_after: Number of seconds until the request can be retried.
        """
        rate = cls.get_rate(request, scope)
        if not rate:
            return True, None, None

        num_requests, duration, period = cls.parse_rate(rate)
        key = cls.get_cache_key(request, scope)
        now = time()
        history = cache.get(key, [])
        history = [timestamp for timestamp in history if timestamp > now - duration]
        logger.debug('accounts.services.rate_limit.RateLimitService.check_request():'
                     f'history: {history}')
        if len(history) >= num_requests:
            retry_after = ceil(history[-1] + duration - now)
            return False, max(retry_after, 1), period

        history.insert(0, now)
        cache.set(key, history, duration)
        return True, None, None

    @classmethod
    def enforce_request(cls, request, scope: str) -> None:
        """
        If the request is not allowed raises a LimitExceeded exception

        Args:
            request: Request object containing metadata about the current request.
            scope: String identifying the rate-limiting scope.

        Returns:
              None
        """
        allowed, retry_after, period = cls.check_request(request, scope)
        logger.debug("accounts.services.rate_limit.RateLimitService.enforce_request():"
                     f"scope:{scope} allowed:{allowed} retry_after: {retry_after}{period if period else ''}")
        if not allowed:
            raise LimitExceeded(retry_after=retry_after, scope=scope)
