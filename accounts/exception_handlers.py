import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404

from accounts.exceptions import LimitExceeded, TokenRefreshTooOften
from django_project.api import api

logger = logging.getLogger(__name__)

EXCEPTION_CODES = {
    Http404: 404,
    PermissionDenied: 403,
    ValueError: 404,
    ValidationError: 404,
}

@api.exception_handler(TokenRefreshTooOften)
def token_refresh_too_often_handler(request, exc):
    return api.create_response(
        request,
        {
            "detail": "Token refresh limit exceeded",
            "retry_after": exc.retry_after,
        },
        status=429,
        headers={
            "Retry-After": str(exc.retry_after)
        }
    )


@api.exception_handler(LimitExceeded)
def rate_limit_handler(request, exc):
    headers = {}
    if exc.retry_after is not None:
        headers["Retry-After"] = str(exc.retry_after)
    return api.create_response(
        request,
        {
            "detail": str(exc),
            "retry_after": exc.retry_after,
            "scope": exc.scope,
        },
        status=429,
        headers=headers,
    )

@api.exception_handler(Exception)
def exception_handler(request, exc):
    logger.error(f"accounts.exception_handlers.exception_handler(): exception: {exc}")
    for exc_type, status in EXCEPTION_CODES.items():
        if isinstance(exc, exc_type):
            logger.error(f"accounts.exception_handlers.exception_handler(): caught {exc_type}: {exc}")
            return api.create_response(
                request,
                {"status": "error", "detail": str(exc)},
                status=status
            )
    return api.create_response(
        request,
        {"status": "error",
         "detail": str(exc)
         },
        status=500
    )

