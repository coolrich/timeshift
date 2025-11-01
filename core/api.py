from logging import getLogger
from typing import Optional, List

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from ninja import NinjaAPI
from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Response

from core.auth import SessionOrToken
from core.models import VirtualClock
from .schemas import TimeData, VirtualClockInfo, ClockUpdateRequest, \
    CreateClockRequest, TimeDataUpdate, ErrorClockResponse, UserDataResponse
from .services import VirtualClockController
from .utils import TimeService

logger = getLogger(__name__)
User = get_user_model()
api = NinjaAPI(auth=SessionOrToken())
router = Router()
api.add_router("/time", router)

# TODO: review the method
def get_v_clock_controller(request, clock_id: Optional[str] = None) -> tuple[VirtualClockController, User]:
    user = request.auth
    if clock_id:
        try:
            clock = user.virtual_clocks.get(id=clock_id)
        except (VirtualClock.DoesNotExist, ValueError):
            logger.error(f"Clock not found for user {user} id: {clock_id}")
            try:
                logger.info(f"Looking for shared clock with id: {clock_id}")
                clock = VirtualClock.objects.get(id=clock_id)
            except (VirtualClock.DoesNotExist, ValueError, ValidationError):
                logger.error(f"Clock not found for id: {clock_id}")
                raise HttpError(status_code=404, message="Not found")

        if not (user == clock.user_owner or user in clock.allowed_users.all()):
            raise HttpError(status_code=403, message="Permission denied")
        elif clock.user_owner == user:
            logger.info(f"User {user} requested it's own clock {clock_id}")
        else:
            logger.info(f"Allowed user {user} requested clock {clock_id} of user owner {clock.user_owner}")
    else:
        # TODO: review this logic
        clock = VirtualClock.objects.filter(user_owner=user).first()
        if not clock:
            logger.info(f"No clocks found for user {user}, creating a default one")
            clock = VirtualClock.objects.create(user=user, name="Default Clock")
    return VirtualClockController(clock), user


@router.get("/testuser", response=UserDataResponse)
def test(request):
    user = request.auth
    return UserDataResponse(
        id=user.id,
        username=user.username
    )

# @router.get("/", response=TimeResponse)
# def get_time(request, clock_id: str):
#     controller = get_v_clock_controller(request, clock_id)
#     return {
#         "status": "success",
#         "data": TimeData(
#             id=controller.virtual_clock.public_id,
#             name=controller.virtual_clock.name,
#             time=controller.get_time(),
#             tick_enabled=controller.tick_status
#         )
#     }


# @router.post("/", response=TimeData)
# def set_time(request, payload: TimeRequest, clock_id: Optional[str] = None):
#     controller = get_v_clock_controller(request, clock_id)
#     is_valid, new_time = TimeService.validate_time_format(payload.time)
#     if not is_valid:
#         raise HttpError(400, "Invalid time format")
#     controller.set_time(new_time)
#     controller.commit()
#     return {
#         "status": "success",
#         "data": TimeData(
#             id=controller.virtual_clock.public_id,
#             name=controller.virtual_clock.name,
#             time=controller.get_time(),
#             tick_enabled=controller.tick_status
#         ),
#         "message": "Time updated successfully"
#     }


# @router.get("/toggle/", response=TickStatusResponse)
# def toggle_tick(request, clock_id: Optional[str] = None):
#     controller = get_v_clock_controller(request, clock_id)
#     controller.toggle_tick()
#     controller.commit()
#     return {
#         "status": "success",
#         "tick_enabled": controller.tick_status,
#         "message": "Tick status toggled successfully"
#     }


# @router.post("/tick/", response=TickStatusResponse)
# def set_tick(request, payload: TickSetRequest, clock_id: Optional[str] = None):
#     controller = get_v_clock_controller(request, clock_id)
#     controller.toggle_tick(payload.enabled)
#     controller.commit()
#     return {
#         "status": "success",
#         "tick_enabled": controller.tick_status,
#         "message": "Tick status updated successfully"
#     }



# TODO: review this method
@router.post("/setreal/", response={200:TimeData, 403:ErrorClockResponse})
def set_real(request, clock_id: Optional[str] = None):
    controller, user = get_v_clock_controller(request, clock_id)
    controller.set_real_time()
    controller.save()
    return {
        "status": "success",
        "data": TimeData(
            clock_id=controller.virtual_clock.id,
            user_owner_id=controller.get_user_owner().id,
            name=controller.virtual_clock.name,
            time=controller.get_time(),
            tick_enabled=controller.tick_status
        ),
        "message": "Time set to real time"
    }

# ================
# CRUD ops
# ================


@router.post("/clocks/", response={201:VirtualClockInfo, 403:ErrorClockResponse})
def create_clock(request, payload: Optional[CreateClockRequest] = None):
    logger.debug(f"create_clock() request: {request}")
    user = request.auth
    logger.debug(f"create_clock() user: {user} | name: {payload.name if payload else None}")
    clock = VirtualClock.objects.create(
        user_owner=user,
        name=payload.name if payload else None
        # f"Clock {VirtualClock.objects.filter(user_owner=user).count() + 1}"
    )
    return Response(data=VirtualClockInfo(
        id=str(clock.id),
        name=clock.name,
        tick_enabled=clock.tick_enabled,
        current_time=clock.current_time.isoformat()
    ),
        status=201)

# 🟢 RETRIEVE (отримати один годинник)
@router.get("/clocks/{clock_id}/", response={200:TimeData, 403:ErrorClockResponse})
def retrieve_clock(request, clock_id: str):
    controller, user = get_v_clock_controller(request, clock_id)

    return TimeData(
        clock_id=controller.virtual_clock.id,
        user_owner_id=controller.get_user_owner().id,
        name=controller.virtual_clock.name,
        time=controller.get_time(),
        allowed_users=list(controller.virtual_clock.allowed_users.values_list("id", flat=True)),
        tick_enabled=controller.tick_status
    )

# 🟢 LIST (отримати всі годинники)
@router.get("/clocks/", response={200:List[TimeData], 403:ErrorClockResponse})
def list_clocks(request):
    user = request.auth
    clocks = []

    for controller in (VirtualClockController(c) for c in VirtualClockController.list_clocks(user)):
        clock = controller.virtual_clock
        owner = controller.get_user_owner()

        # показуємо allowed_users лише власнику

        if owner == user:
            allowed_users = list(clock.allowed_users.values_list("id", flat=True))

            clocks.append(TimeData(
                clock_id=clock.id,
                user_owner_id=owner.id,
                name=clock.name,
                time=controller.get_time(),
                allowed_users=allowed_users,
                tick_enabled=controller.tick_status,
            ))
        else:
            clocks.append(TimeData(
                clock_id=clock.id,
                user_owner_id=owner.id,
                name=clock.name,
                time=controller.get_time(),
                tick_enabled=controller.tick_status,
            ))

    return clocks


@router.put("/clocks/", response={200:TimeDataUpdate, 403:ErrorClockResponse})
def update_clock(request, payload: ClockUpdateRequest):
    payload_dict = payload.dict()
    logger.debug(f"core.api.update_clock(): payload_dict: {payload_dict}")
    clock_id = payload_dict["id"]
    controller, user = get_v_clock_controller(request, clock_id)
    clock = controller.virtual_clock
    changed_fields = []

    # 1) Оновлення часу
    if payload_dict.get("time") is not None:
        is_valid, new_time = TimeService.validate_time_format(payload_dict["time"])
        if not is_valid:
            raise HttpError(400, "Invalid time format")
        controller.set_time(new_time)
        changed_fields.append("time")

    # 2) Оновлення tick
    if payload_dict.get("tick_enabled") is not None:
        controller.toggle_tick(payload_dict["tick_enabled"])
        changed_fields.append("tick_enabled")

    # 3) Оновлення імені
    if payload_dict.get("name") is not None:
        name = (payload_dict["name"] or "").strip()
        controller.set_clock_name(name)
        changed_fields.append("name")

    relevant_keys = {"allowed_users", "add_users", "remove_users"}
    keys = relevant_keys & payload_dict.keys()
    logger.info(f"core.api.update_clock(): keys: {keys}")
    keys_set = {k for k in keys if payload_dict[k] is not None}
    if relevant_keys & keys_set:
        # 4) редагування allowed_users
        if clock.user_owner != user:
            logger.info(f"User {user.username} is not the owner of clock {clock.id}")
            return 403, ErrorClockResponse(status="error", detail="Permission denied")
        filtered_payload = {k: v for k, v in payload_dict.items() if k in relevant_keys and v is not None}
        controller.update_allowed_users(filtered_payload)
        changed_fields.append("allowed_users")

    logger.info(f"core.api.update_clock(): changed_fields: {changed_fields}")
    controller.save()
    return TimeDataUpdate(
        id=clock.id,
        name=clock.name if "name" in changed_fields else None,
        time=controller.get_time() if "time" in changed_fields else None,
        tick_enabled=controller.tick_status if "tick_enabled" in changed_fields else None,
        allowed_users=list(clock.allowed_users.values_list("id", flat=True)) if "allowed_users" in changed_fields else None,
        changed_fields=changed_fields
    )




@router.delete(
    "/clocks/{clock_id}",
    response={204: None, 404: ErrorClockResponse, 403: ErrorClockResponse},
)
def delete_clock(request, clock_id: str):
    controller, user = get_v_clock_controller(request, clock_id)
    controller.virtual_clock.delete()
    return HttpResponse(status=204)
