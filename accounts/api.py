from logging import getLogger

from django.contrib.auth import get_user_model
from ninja import Router

from .schemas import UserDataUpdate, ErrorUserResponse, UserUpdateRequest
from .services import UserController

logger = getLogger(__name__)
User = get_user_model()
router = Router()

# @router.get("/test/", response=UserDataResponse,
#             description='Check if api is working')
# def test(request):
#     user = request.auth
#     return UserDataResponse(
#         id=user.id,
#         username=user.username
#     )

@router.put("/update/", response={200: UserDataUpdate, 403: ErrorUserResponse})
def update_user(request, payload: UserUpdateRequest):
    """
    Update a user.

    Parameters:
      - refresh_token: bool

    """
    payload_dict = payload.dict()
    logger.debug(f"core.api.update_clock(): payload_dict: {payload_dict}")
    changed_fields = []
    user = UserController(request.auth)
    user.update(payload)
    changed_fields.append("api_token")

    # logger.info(f"core.api.update_clock(): changed_fields: {changed_fields}")
    user.save()
    logger.info(f"core.api.update_clock(): new token: {user.api_token}")
    return UserDataUpdate(
        api_token=user.api_token
    )
