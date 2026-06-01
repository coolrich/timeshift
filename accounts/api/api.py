from logging import getLogger

from django.contrib.auth import get_user_model
from ninja import Router

from accounts.schemas import UserDataUpdate, ErrorUserResponse, UserUpdateRequest
from accounts.services.user import UserController

logger = getLogger(__name__)
User = get_user_model()


def create_user_router() -> Router:
    """
    Factory function to create a new Router instance with user endpoints.
    """
    router = Router()

    # Приклад оновлення користувача
    @router.put("/update/", response={200: UserDataUpdate, 403: ErrorUserResponse})
    def update_user(request, payload: UserUpdateRequest):
        """
        Update a user.

        Parameters:
          - refresh_token: bool
        """
        payload_dict = payload.dict()
        logger.debug(f"update_user(): payload_dict: {payload_dict}")
        changed_fields = []
        user = request.auth
        logger.debug(f"update_user(): user: {user}")
        user_ctrl = UserController(user)

        if payload_dict.get("refresh_token"):
            user_ctrl.update_token()
            changed_fields.append("api_token")

        user_ctrl.save()
        logger.info(f"update_user(): new token: {user_ctrl.api_token}")

        return UserDataUpdate(api_token=user_ctrl.api_token)

    return router
