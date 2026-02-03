import logging
from typing import Type

from django.contrib.auth import get_user_model
from django.utils import timezone

from .exceptions import TokenRefreshTooOften
from .models import TimeShiftUser

logger = logging.getLogger(__name__)
User = get_user_model()

class UserController:
    # TOKEN_REFRESH_COOLDOWN = timedelta(minutes=5)

    def __init__(self, user):
        self._user: TimeShiftUser = user

    @property
    def user(self) -> User:
        return self._user

    @property
    def api_token(self) -> str:
        return self._user.api_token

    def update_token(self, save: bool = True) -> Type['UserController']:
        now = timezone.now()

        if self._user.token_last_refreshed_at:
            delta = now - self._user.token_last_refreshed_at
            if delta < User._TOKEN_REFRESH_COOLDOWN:
                raise TokenRefreshTooOften(
                    retry_after=User._TOKEN_REFRESH_COOLDOWN - delta
                )
        self._user.refresh_token()
        if save:
            self._user.save()
        return self

    def save(self):
        self._user.save()
        return self