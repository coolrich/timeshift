from ninja import NinjaAPI

from accounts import api as accounts_api
from core import api as core_api
from core.auth import SessionOrToken

api = NinjaAPI(auth=SessionOrToken(),
               title="TimeShift API",
               description="TimeShift API",
               version="1.0.0")
api.add_router("/user", accounts_api.router, tags=["User"])
api.add_router("/clock", core_api.router, tags=["Clock"])
