from typing import Optional, List, Tuple

from ninja import Schema


# ======================
# Запити
# ======================

class BaseClockRequest(Schema):
    clock_id: int
    tick_enabled: bool = False

class TimeRequest(Schema):
    time: str  # ISO 8601, наприклад: "2025-08-22T10:15:00+00:00"

class TickSetRequest(Schema):
    enabled: bool  # True або False

# ======================
# Відповіді
# ======================

# Базова схема з усіма полями
class BaseClockSchema(Schema):
    user_owner_id: int
    clock_id: int
    name: str | None
    time: str
    speed: float
    tick_enabled: bool


# Схема для відповіді (всі поля обов'язкові)
class TimeData(BaseClockSchema):
    allowed_users: Optional[List[int] | Tuple[int]] = None


class TimeDataUpdate(Schema):
    clock_id: Optional[int] = None
    name: Optional[str] = None
    time: Optional[str] = None
    speed: Optional[float] = None
    tick_enabled: Optional[bool] = None
    allowed_users: Optional[List[int]] = None  # остаточний список allowed_users після оновлення
    changed_fields: List[str] = []            # які поля реально змінилися

# Схема для PUT-запиту (поля необов'язкові)
class ClockUpdateRequest(Schema):
    clock_id: int
    name: Optional[str] = None
    time: Optional[str] = None
    speed: Optional[float] = None
    tick_enabled: Optional[bool] = False
    allowed_users: Optional[List[int]] = None   # повна заміна
    add_users: Optional[List[int]] = None       # додати
    remove_users: Optional[List[int]] = None    # видалити
    # add datetime validation

    # def validate_time(self):
    #     if self.time:
    #         try:
    #             datetime.fromisoformat(self.time)
    #         except ValueError:
    #             raise ValueError("Invalid time format")


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
    id: int
    name: Optional[str] = None
    tick_enabled: bool
    current_time: str  # ISO 8601


# class VirtualClockListResponse(Schema):
#     status: str
#     clocks: List[VirtualClockInfo]

class CreateClockRequest(Schema):
    name: Optional[str] = None
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
    detail: str | None = None
