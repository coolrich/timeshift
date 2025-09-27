from ninja import Schema
from typing import Optional, List


# ======================
# Запити
# ======================

class TimeRequest(Schema):
    time: str  # ISO 8601, наприклад: "2025-08-22T10:15:00+00:00"

class TickSetRequest(Schema):
    enabled: bool  # True або False

# ======================
# Відповіді
# ======================

# Базова схема з усіма полями
class BaseClockSchema(Schema):
    id: int
    name: str
    time: str
    allowed_users: List[int]
    tick_enabled: bool

# Схема для відповіді (всі поля обов'язкові)
class TimeData(BaseClockSchema):
    pass

class TimeDataUpdate(Schema):
    id: Optional[int] = None
    name: Optional[str] = None
    time: Optional[str] = None
    tick_enabled: Optional[bool] = None
    allowed_users: Optional[List[int]] = None  # остаточний список allowed_users після оновлення
    changed_fields: List[str] = []            # які поля реально змінилися

# Схема для PUT-запиту (поля необов'язкові)
class ClockUpdateRequest(Schema):
    id: int
    name: Optional[str] = None
    time: Optional[str] = None
    tick_enabled: Optional[bool] = None
    allowed_users: Optional[List[int]] = None   # повна заміна
    add_users: Optional[List[int]] = None       # додати
    remove_users: Optional[List[int]] = None    # видалити

class TickStatusResponse(Schema):
    status: str
    tick_enabled: bool
    message: Optional[str] = None

class TimeResponse(Schema):
    status: str
    data: TimeData
    message: Optional[str] = None

class SetRealResponse(Schema):
    status: str
    data: TimeData
    message: Optional[str] = None

class VirtualClockInfo(Schema):
    id: str  # UUID
    name: Optional[str]
    tick_enabled: bool
    current_time: str  # ISO 8601


# class VirtualClockListResponse(Schema):
#     status: str
#     clocks: List[VirtualClockInfo]

class CreateClockRequest(Schema):
    name: Optional[str]
    # Authorization: str

# class ClockUpdateRequest(Schema):
#     time: Optional[str] = None
#     tick_enabled: Optional[bool] = None
#     name: Optional[str] = None  # ← додано

class DeleteClockResponse(Schema):
    status: str
    message: str

class ErrorClockResponse(Schema):
    status: str
    detail: str