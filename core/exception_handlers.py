from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
import logging
from core.models import VirtualClock
from core.api import api
from ninja.errors import HttpError

logger = logging.getLogger(__name__)

EXCEPTION_CODES = {
    Http404: 404,
    PermissionDenied: 403,
    VirtualClock.DoesNotExist: 404,
    ValueError: 404,
    ValidationError: 404,
}


@api.exception_handler(Exception)
def exception_handler(request, exc):
    logger.error(f"exception_handler(): exception: {exc}")
    for exc_type, status in EXCEPTION_CODES.items():
        if isinstance(exc, exc_type):
            logger.error(f"exception_handler(): caught {exc_type}: {exc}")
            return api.create_response(
                request,
                {"status":"error", "detail": str(exc)},
                status=status
            )
    return api.create_response(
        request,
        {"status":"error", "detail": str(exc)},
        status=500
    )
