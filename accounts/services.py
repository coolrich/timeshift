import logging

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

    def update_token(self) -> User:
        now = timezone.now()

        if self.user.token_last_refreshed_at:
            delta = now - self.user.token_last_refreshed_at
            if delta < User._TOKEN_REFRESH_COOLDOWN:
                raise TokenRefreshTooOften(
                    retry_after=User._TOKEN_REFRESH_COOLDOWN - delta
                )
        self.user.refresh_token()
        return self._user

    def save(self):
        self.user.save()
        return self._user