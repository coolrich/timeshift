from ninja import NinjaAPI

from accounts.api.api import create_user_router
from core.api.api import create_clock_router
from core.api.throttles import GlobalUserThrottle
from core.auth import SessionOrToken

api = NinjaAPI(auth=SessionOrToken(),
               throttle=GlobalUserThrottle(),
               title="TimeShift API",
               description="TimeShift API",
               version="1.0.0")

user_router = create_user_router()
clocks_router = create_clock_router()
api.add_router("/user/", user_router, tags=["User"])
api.add_router("/clocks/", clocks_router, tags=["Clock"])
