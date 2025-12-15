from ninja import Schema
from typing import Optional, List

# ======================
# Запити
# ======================

class UserUpdateRequest(Schema):
    """
    Update user.
    """
    # username: Optional[str] = None
    refresh_token: Optional[bool] = False

# ======================
# Відповіді
# ======================

class UserDataUpdate(Schema):
    # username: Optional[str] = None
    api_token: Optional[str] = None

class ErrorUserResponse(Schema):
    status: str
    detail: str | None = None
