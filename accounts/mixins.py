from babel.dates import format_timedelta
from django.contrib import messages
from django.http import HttpResponse

from accounts.exceptions import LimitExceeded
from accounts.services.rate_limit import RateLimitService
from logging import getLogger

logger = getLogger(__name__)

class PostRateLimitMixin:
    throttle_methods = {"POST"}
    throttle_scope = None

    def get_throttle_scope(self):
        return self.throttle_scope

    def should_limit_request(self, request) -> bool:
        return request.method.upper() in self.throttle_methods and bool(self.get_throttle_scope())

    @staticmethod
    def handle_limit_exceeded(exc: LimitExceeded):
        response = HttpResponse(str(exc), status=429)
        response['period'] = str(exc.period)
        # if exc.retry_after is not None:
        #     response["Retry-After"] = str(exc.retry_after)
        return response

    def dispatch(self, request, *args, **kwargs):
        logger.debug("accounts.mixins.PostRateLimitMixin.dispatch():"
                     "")
        if self.should_limit_request(request):
            try:
                RateLimitService.enforce_request(request, self.get_throttle_scope())
            except LimitExceeded as exc:
                # The message will be sent and actions will be limited.
                logger.debug("accounts.mixins.PostRateLimitMixin.dispatch():"
                             "limit exceeded")
                r = self.handle_limit_exceeded(exc)
                text = r.text
                period = r['period']
                logger.debug("accounts.mixins.PostRateLimitMixin.dispatch():"
                             f"message: {text}")
                # just a message without a specific return
                messages.info(
                    request,
                    f"{text}. Try after {exc.retry_after}{period}."
                )

        return super().dispatch(request, *args, **kwargs)
