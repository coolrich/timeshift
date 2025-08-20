from ninja import Schema
from datetime import datetime

class TimeRequest(Schema):
    time: str

class TimeResponse(Schema):
    time: str
    is_real: bool
    tick_enabled: bool

class StatusResponse(Schema):
    status: str
    current_time: str | None = None
    tick_enabled: bool | None = None
    error: str | None = None


class ToggleTickRequest(Schema):
    enabled: bool