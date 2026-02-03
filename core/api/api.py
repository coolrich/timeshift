from logging import getLogger
from typing import Optional, List, Union

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from ninja import Router, Body
from ninja.responses import Response
from ninja.errors import HttpError

from core.schemas import (
    TimeData, VirtualClockInfo, ClockUpdateRequest,
    CreateClockRequest, TimeDataUpdate, ErrorClockResponse,
    BaseClockRequest, TimeResponse, BaseClockSchema
)
from core.services import VirtualClockController
from core.utils import TimeService
from core.models import VirtualClock
from django_project import settings

logger = getLogger(__name__)
User = get_user_model()


async def get_v_clock_controller(
        request, clock_id: int
) -> tuple[VirtualClockController, User]:
    user = request.auth
    clock = await user.virtual_clocks.filter(id=clock_id) \
        .prefetch_related("allowed_users") \
        .select_related("user_owner") \
        .afirst()

    if not clock:
        logger.debug(f"Clock {clock_id} not found for user {user.id}")
        clock = await user.shared_clocks.select_related("user_owner").filter(id=clock_id).afirst()
        if not clock:
            raise HttpError(status_code=404, message="Not found")
        logger.debug(f"Shared clock {clock_id} found for user {user.id} of owner {clock.user_owner_id}")

    if clock.user_owner != user:
        allowed = await clock.allowed_users.filter(id=user.id).aexists()
        if not allowed:
            raise HttpError(status_code=403, message="Permission denied")
        logger.info(
            f"Allowed user {user.id} requested clock {clock_id} of owner {clock.user_owner_id}"
        )
    else:
        logger.info(f"Owner {user.username}(id:{user.id}) requested own clock {clock.name}(id:{clock_id})")

    return VirtualClockController(clock), user


def create_clock_router() -> Router:
    """
    Factory function to create a new Router instance with all clock endpoints.
    Useful for tests or multiple API instances.
    """
    router = Router()
    if settings.DEBUG:
        @router.get("/test", response={200: dict})
        async def test_route(request):
            return {"message": "Hello from test route!"}

    @router.post("/setreal", response={200: Union[TimeResponse | BaseClockSchema], 403: ErrorClockResponse})
    async def set_real(request, payload: BaseClockRequest):
        clock_id = payload.clock_id
        controller, user = await get_v_clock_controller(request, clock_id)
        await controller.set_real_time_async(tick_enabled=payload.tick_enabled)
        if controller.get_user_owner() == user:
            allowed_users = [user_id async for user_id in
                             controller.virtual_clock.allowed_users.values_list("id", flat=True)]
            return {
                "status": "success",
                "data": TimeData(
                    clock_id=controller.virtual_clock.id,
                    user_owner_id=controller.get_user_owner().id,
                    name=controller.virtual_clock.name,
                    time=controller.get_iso_time(),
                    tick_enabled=controller.tick_status,
                    speed=controller.get_clock_speed(),
                    allowed_users=list(allowed_users),
                ),
                "message": "Time set to real time"
            }
        else:
            return {
                "status": "success",
                "data": BaseClockSchema(
                    clock_id=controller.virtual_clock.id,
                    user_owner_id=controller.get_user_owner().id,
                    name=controller.virtual_clock.name,
                    time=controller.get_iso_time(),
                    tick_enabled=controller.tick_status,
                    speed=controller.get_clock_speed(),
                ),
                "message": "Time set to real time"
            }

    @router.post("", response={201: VirtualClockInfo, 403: ErrorClockResponse})
    async def create_clock(request, payload: Optional[CreateClockRequest] = None):
        user = request.auth
        clock = await VirtualClockController.create_clock_async(
            user, name=payload.name if payload else None
        )
        return Response(
            data=VirtualClockInfo(
                id=clock.id,
                name=clock.name,
                tick_enabled=clock.tick_enabled,
                current_time=clock.current_time.isoformat()
            ),
            status=201
        )

    @router.get("/{clock_id}", response={200: TimeData, 403: ErrorClockResponse}, url_name='api-retrieve-clock')
    async def retrieve_clock(request, clock_id: int):
        controller, user = await get_v_clock_controller(request, clock_id)
        allowed_users = [user_id async for user_id in controller.virtual_clock.allowed_users.
        values_list("id", flat=True)]
        return TimeData(
            clock_id=controller.virtual_clock.id,
            user_owner_id=controller.get_user_owner().id,
            name=controller.virtual_clock.name,
            time=controller.get_iso_time(),
            speed=controller.get_clock_speed(),
            allowed_users=allowed_users,
            tick_enabled=controller.tick_status
        )

    @router.get("", response={200: List[TimeData], 403: ErrorClockResponse}, url_name='api-list-clocks')
    async def list_clocks(request):
        logger.info(f"core.api.api.list_clocks(): begin")
        user = request.auth
        clocks = []
        all_clocks = await VirtualClockController.alist_clocks(user)
        controllers = (VirtualClockController(c) async for c in all_clocks)
        async for controller in controllers:
            clock = controller.virtual_clock
            owner = await sync_to_async(controller.get_user_owner)()
            if owner == user:
                # allowed_users = list(await clock.allowed_users.values_list("id", flat=True))
                allowed_users = tuple([user_id async for user_id in clock.allowed_users.values_list("id", flat=True)])
                clocks.append(TimeData(
                    clock_id=clock.id,
                    user_owner_id=owner.id,
                    name=clock.name,
                    time=controller.get_iso_time(),
                    speed=controller.get_clock_speed(),
                    allowed_users=allowed_users,
                    tick_enabled=controller.tick_status,
                ))
            else:
                clocks.append(TimeData(
                    clock_id=clock.id,
                    user_owner_id=owner.id,
                    name=clock.name,
                    time=controller.get_iso_time(),
                    speed=controller.get_clock_speed(),
                    tick_enabled=controller.tick_status,
                ))
        return clocks

    @router.put("", response={200: TimeDataUpdate, 403: ErrorClockResponse}, url_name='api-update-clock')
    async def update_clock(request, payload: ClockUpdateRequest = Body(...)):
        logger.debug(f"core.api.api.update_clock: {payload}")
        payload_dict = payload.dict()
        clock_id = payload_dict["clock_id"]
        controller, user = await get_v_clock_controller(request, clock_id)
        clock = controller.virtual_clock
        changed_fields = []

        if payload_dict.get("time"):
            is_valid, new_time = TimeService.validate_time_format(payload_dict["time"])
            if not is_valid:
                raise HttpError(400, "Invalid time format")
            controller.set_time(new_time, save=False)
            changed_fields.append("time")

        if payload_dict.get("speed"):
            new_speed = payload_dict["speed"]
            # controller.set_clock_speed(new_speed, save=False)
            await controller.set_clock_speed_async(new_speed, save=False)
            changed_fields.append("speed")

        if payload_dict.get("tick_enabled") is not None:
            controller.toggle_tick(payload_dict["tick_enabled"], save=False)
            changed_fields.append("tick_enabled")

        if payload_dict.get("name"):
            name = (payload_dict["name"] or "").strip()
            controller.set_clock_name(name, save=False)
            changed_fields.append("name")

        relevant_keys = {"allowed_users", "add_users", "remove_users"}
        keys = relevant_keys & payload_dict.keys()
        keys_set = {k for k in keys if payload_dict[k]}
        if relevant_keys & keys_set:
            if clock.user_owner != user:
                return 403, ErrorClockResponse(status="error", detail="Permission denied")
            filtered_payload = {k: v for k, v in payload_dict.items() if k in relevant_keys and v}
            await controller.update_allowed_users_async(filtered_payload, save=False)
            changed_fields.append("allowed_users")

        await controller.save_async()

        allowed_users = [user_id async for user_id in clock.allowed_users.values_list("id", flat=True)]
        return TimeDataUpdate(
            clock_id=clock.id,
            name=clock.name if "name" in changed_fields else None,
            time=controller.get_iso_time() if "time" in changed_fields else None,
            speed=controller.get_clock_speed() if "speed" in changed_fields else None,
            tick_enabled=controller.tick_status if "tick_enabled" in changed_fields else None,
            allowed_users=allowed_users if "allowed_users" in changed_fields else None,
            changed_fields=changed_fields
        )

    @router.delete(
        "/{clock_id}",
        response={204: None, 404: ErrorClockResponse, 403: ErrorClockResponse},
    )
    async def delete_clock(request, clock_id: int):
        controller, user = await get_v_clock_controller(request, clock_id)
        await controller.delete_async(user)
        return HttpResponse(status=204)

    return router
