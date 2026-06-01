from math import ceil
from time import time

from django.conf import settings
from django.core.cache import cache

from accounts.exceptions import LimitExceeded
from accounts.services.throttle_helper import build_user_rates


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
    def parse_rate(rate: str) -> tuple[int, int]:
        """Get a rate in as a (number,period)"""
        num_str, period = rate.split("/", 1)
        periods = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
        }
        return int(num_str), periods[period]

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
    def check_request(cls, request, scope: str) -> tuple[bool, int | None]:
        """
        Returns a tuple (allowed, retry_after).

        Returns:
            tuple[bool, int]:
                - allowed: True if the request is permitted, otherwise False.
                - retry_after: Number of seconds until the request can be retried.
        """
        rate = cls.get_rate(request, scope)
        if not rate:
            return True, None

        num_requests, duration = cls.parse_rate(rate)
        key = cls.get_cache_key(request, scope)
        now = time()
        history = cache.get(key, [])
        history = [timestamp for timestamp in history if timestamp > now - duration]

        if len(history) >= num_requests:
            retry_after = ceil(history[-1] + duration - now)
            return False, max(retry_after, 1)

        history.insert(0, now)
        cache.set(key, history, duration)
        return True, None

    @classmethod
    def enforce_request(cls, request, scope: str) -> None:
        allowed, retry_after = cls.check_request(request, scope)
        if not allowed:
            raise LimitExceeded(retry_after=retry_after, scope=scope)
