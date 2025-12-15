import logging

from django.contrib.auth import get_user_model

from .models import generate_api_token, TimeShiftUser
from .schemas import UserUpdateRequest

logger = logging.getLogger(__name__)
User = get_user_model()

class UserController:

    def __init__(self, user):
        self._user: TimeShiftUser = user

    @property
    def user(self) -> User:
        return self._user

    @property
    def api_token(self) -> str:
        return self._user.api_token

    def update(self, payload: UserUpdateRequest) -> User:
        # if payload.username is not None:
        #     is_exist = User.objects.filter(username=payload.username).exists()
        #     if is_exist:
        #         raise HttpError(400, "Username already exists")
        #
        #     self.user.username = payload.username
        if payload.refresh_token:
            self.user.api_token = generate_api_token(User)
        return self._user

    def save(self):
        self.user.save()
        return self._user