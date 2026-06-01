import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from ninja.errors import HttpError
from ninja.security.base import AuthBase

from accounts.services.throttle_helper import build_user_rates
from core.services import AuthHelper

logger = logging.getLogger(__name__)

User = get_user_model()


class SessionOrToken(AuthBase):
    openapi_type = "http"
    openapi_scheme = "bearer"

    def __call__(self, request):
        return self.authenticate(request)

    @staticmethod
    def _attach_rates_cache(user: User) -> User:
        logger.debug(f"core.auth.SessionOrToken._attach_rates_cache():")
        user.rates_cache = build_user_rates(user)
        return user

    def authenticate(self, request) -> AbstractBaseUser | None | Any:
        logger.info("==============================================")
        logger.debug(f"core.auth.SessionOrToken.authenticate():")
        # 1) Session auth
        if getattr(request, "user", None) and request.user.is_authenticated:
            logger.debug(f"Authenticated user from session: {request.user}")
            logger.debug(f"Action: {request.method} {request.path}")

            return self._attach_rates_cache(request.user)

        # 2) Token auth
        auth = request.headers.get("Authorization", "")

        logger.debug(f"Attempting to authenticate user from token: {AuthHelper.mask_token(auth)}")

        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()

            try:
                user = (
                    User.objects
                    .get(_api_token=token)
                )
            except User.DoesNotExist:
                logger.debug(f"User not found for token: {AuthHelper.mask_token(token)}")
                raise HttpError(401, "Invalid authentication token")

            logger.debug(f"Authenticated user {user.username} from token: {AuthHelper.mask_token(token)}")
            logger.debug(f"Action: {request.method} {request.path}")

            return self._attach_rates_cache(user)

        return None
