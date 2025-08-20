from ninja import Router
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from ninja.errors import HttpError

from .schemas import TimeRequest, TimeResponse, StatusResponse, ToggleTickRequest
from .services import TimeShiftController, TimeService
from core.models import UserSimulationState
from core.auth import AuthBearer

router = Router(auth=AuthBearer())
# router = Router()

User = get_user_model()


def get_simulator(request) -> TimeShiftController:
    """Повертає TimeShiftController для аутентифікованого користувача."""
    user: User = request.user
    if not user.is_authenticated:
        raise HttpError(401, "Unauthenticated")
    state, _ = UserSimulationState.objects.get_or_create(user=user)
    return TimeShiftController(state)


@router.get("/test/")
def tests(request):
    return f"Hello, {request.user}!"

@router.get("/time/", response=TimeResponse)
def get_time(request):
    simulator = get_simulator(request)
    return {
        "time": simulator.now().isoformat(),
        "is_real": simulator.is_real(),
        "tick_enabled": simulator.tick_enabled,
    }

@router.post("/time/", response={200: StatusResponse})
def set_time(request, payload: TimeRequest):
    simulator = get_simulator(request)
    is_valid, new_time = TimeService.validate_time_format(payload.time)
    if not is_valid:
        raise HttpError(400, "Invalid time format")

    simulator.set_time(new_time)
    simulator.user.save()
    return {"status": "success", "current_time": simulator.now().isoformat()}


@router.post("/tick/", response=StatusResponse)
def toggle_tick(request, payload: ToggleTickRequest):
    simulator = get_simulator(request)
    simulator.toggle_tick(payload.enabled)
    simulator.user.save()
    return {"status": "success", "tick_enabled": simulator.tick_enabled}


@router.post("/setreal/", response=StatusResponse)
def set_real(request):
    simulator = get_simulator(request)
    simulator.set_real_time()
    simulator.user.save()
    return {"status": "success", "current_time": now().isoformat()}
