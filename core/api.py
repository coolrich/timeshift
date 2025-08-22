from ninja import Router
from django.contrib.auth import get_user_model
from ninja.errors import HttpError

from .schemas import TimeRequest, TimeResponse, StatusResponse, TickSetRequest, SetRealResponse
from .services import TimeShiftController
from .utils import TimeService
from core.models import VirtualClock
from logging import getLogger

logger = getLogger(__name__)

router = Router()
User = get_user_model()


def get_simulator(request) -> TimeShiftController:
    """Повертає TimeShiftController для аутентифікованого користувача."""
    user: User = request.auth
    logger.info(f"get_simulator: user {user} is authenticated")
    state, _ = VirtualClock.objects.get_or_create(user=user)
    return TimeShiftController(state)


@router.get("/test")
def test(request):
    return f"Hello, {request.user}!"


@router.get("/time", response=TimeResponse)
def get_time(request):
    simulator = get_simulator(request)
    return {
        "time": simulator.get_time(),
        "tick_enabled": simulator.tick_status,
    }

@router.post("/time", response=StatusResponse)
def set_time(request, payload: TimeRequest):
    simulator = get_simulator(request)
    is_valid, new_time = TimeService.validate_time_format(payload.time)
    if not is_valid:
        raise HttpError(400, "Invalid time format")

    simulator.set_time(new_time)
    simulator.commit()  # явне збереження
    return {"status": "success", "current_time": simulator.get_time()}


@router.get("/time/toggle", response=StatusResponse)
def toggle_tick(request):
    simulator = get_simulator(request)
    simulator.toggle_tick()
    simulator.commit()
    return {"status": "success", "tick_enabled": simulator.tick_status}

@router.post("/time/tick", response=StatusResponse)
def set_tick(request, payload: TickSetRequest):
    simulator = get_simulator(request)
    simulator.toggle_tick(payload.enabled)
    simulator.commit()
    return {"status": "success", "tick_enabled": simulator.tick_status}


@router.post("/time/setreal", response=SetRealResponse)
def set_real(request):
    simulator = get_simulator(request)
    simulator.set_real()
    simulator.commit()  # явне збереження
    return {"status": "success", "current_time": simulator.get_time()}
