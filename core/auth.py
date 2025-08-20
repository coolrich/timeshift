from ninja.security import HttpBearer
from django.contrib.auth import get_user_model

from core.models import UserSimulationState

User = get_user_model()

class AuthBearer(HttpBearer):
    def authenticate(self, request, token: str) -> User | None:
        try:
            if request.user.is_authenticated:
                return request.user
            else:
                state = UserSimulationState.objects.get(api_token=token)
            return state.user
        except UserSimulationState.DoesNotExist:
            return None
