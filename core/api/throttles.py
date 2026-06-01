from logging import getLogger

from accounts.services.rate_limit import RateLimitService

logger = getLogger(__name__)

from ninja.throttling import SimpleRateThrottle


class BaseUserThrottle(SimpleRateThrottle):

    def get_rate(self):
        request = getattr(self, "request", None)
        if request is None:
            return None
        return RateLimitService.get_rate(request, self.scope)

    def get_cache_key(self, request):
        self.request = request
        user = RateLimitService.get_request_user(request)
        logger.debug(f"core.api.throttles.BaseUserThrottle.get_cache_key(): user: {user}")
        return RateLimitService.get_cache_key(request, self.scope)

    def allow_request(self, request):
        logger.debug(f"core.api.throttles.BaseUserThrottle.allow_request(): start")
        self.request = request
        logger.debug(f"core.api.throttles.BaseUserThrottle.allow_request(): request.auth: {getattr(request, 'auth', None)}")

        user = RateLimitService.get_request_user(request)
        logger.debug(f"core.api.throttles.BaseUserThrottle.allow_request(): user: {user}")
        rate = self.get_rate()
        logger.debug(f"core.api.throttles.BaseUserThrottle.allow_request(): rate: {rate}")
        if not rate:
            return True

        self.rate = rate
        self.num_requests, self.duration = self.parse_rate(rate)

        return super().allow_request(request)

class GlobalUserThrottle(BaseUserThrottle):
    scope = "global"


class ClocksCreateThrottle(BaseUserThrottle):
    scope = "clock_create"
