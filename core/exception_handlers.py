import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from ninja.errors import HttpError

from accounts.exceptions import LimitExceeded
from core.exceptions import ClockLimitExceededError
from core.models import VirtualClock
from django_project.api import api

logger = logging.getLogger(__name__)


def create_exception_handler(an_api):
    EXCEPTION_CODES = {
        Http404: 404,
        PermissionDenied: 403,
        VirtualClock.DoesNotExist: 404,
        ValueError: 404,
        ValidationError: 404,
        HttpError: 400,
        ClockLimitExceededError: 429,
        LimitExceeded: 429,
    }

    @an_api.exception_handler(Exception)
    def exception_handler(request, exc):
        logger.error(f"core.exception_handlers.exception_handler(): exception: {exc}")
        for exc_type, status in EXCEPTION_CODES.items():
            if isinstance(exc, exc_type):
                logger.error(f"core.exception_handlers.exception_handler(): caught {exc_type}: {exc}")
                return an_api.create_response(
                    request,
                    {"status": "error", "detail": str(exc)},
                    status=status
                )
        return an_api.create_response(
            request,
            {"status": "error", "detail": str(exc)},
            status=500
        )

    return exception_handler


e_handler = create_exception_handler(api)
