import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from ninja.errors import HttpError
from ninja.security.base import AuthBase
from core.services import AuthHelper

logger = logging.getLogger(__name__)

User = get_user_model()


class SessionOrToken(AuthBase):
    openapi_type = "http"         # ← ОБОВʼЯЗКОВО
    openapi_scheme = "bearer"     # ← каже OpenAPI що це Bearer Auth

    def __call__(self, request):
        return self.authenticate(request)

    def authenticate(self, request) -> AbstractBaseUser | None | Any:
        # 1) Якщо юзер є в сесії (через django.contrib.auth)
        logger.info("==============================================")
        logger.info(f"Attempting to authenticate user from session: {getattr(request, 'user', None)}")
        if getattr(request, "user", None) and request.user.is_authenticated:
            logger.info(f"Authenticated user from session: {request.user}")
            logger.info(f"Action: {request.method} {request.path}")
            return request.user

        # 2) Bearer токен
        token = request.headers.get('Authorization', None)
        logger.info(f"Attempting to authenticate user from token: {AuthHelper.mask_token(token)}")
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            try:
                user: User = User.objects.get(_api_token=token)
            except User.DoesNotExist:
                logger.info(f"User not found for token: {AuthHelper.mask_token(token)}")
                raise HttpError(401, f"Invalid authentication token")
            logger.info(f"Authenticated user {user.username} from token: {AuthHelper.mask_token(token)}")
            logger.info(f"Action: {request.method} {request.path}")
            return user

        return None

