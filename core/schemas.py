from ninja import Schema
from datetime import datetime

class TimeRequest(Schema):
    time: str

class TimeResponse(Schema):
    time: str
    tick_enabled: bool

class StatusResponse(Schema):
    status: str
    tick_enabled: bool | None = None

class SetRealResponse(Schema):
    status: str
    current_time: datetime

class TickSetRequest(Schema):
    enabled: bool