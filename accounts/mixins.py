from django.http import HttpResponse

from accounts.exceptions import LimitExceeded
from accounts.services.rate_limit import RateLimitService


class PostRateLimitMixin:
    throttle_methods = {"POST"}
    throttle_scope = None

    def get_throttle_scope(self):
        return self.throttle_scope

    def should_limit_request(self, request) -> bool:
        return request.method.upper() in self.throttle_methods and bool(self.get_throttle_scope())

    def handle_limit_exceeded(self, exc: LimitExceeded):
        response = HttpResponse(str(exc), status=429)
        if exc.retry_after is not None:
            response["Retry-After"] = str(exc.retry_after)
        return response

    def dispatch(self, request, *args, **kwargs):
        if self.should_limit_request(request):
            try:
                RateLimitService.enforce_request(request, self.get_throttle_scope())
            except LimitExceeded as exc:
                return self.handle_limit_exceeded(exc)
        return super().dispatch(request, *args, **kwargs)
