from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import tzlocal
import logging

from core.models import UserSimulationState

logger = logging.getLogger(__name__)

class TimeShiftController:
    """
    Контроль симульованого часу:
    - Tick визначає, чи рухається симульований час
    - Симуляція активується при set_time або паузі
    - Reset повертає до реального часу, але зберігає стан tick
    """

    def __init__(self, user: UserSimulationState):
        self.user = user  # user має: simulated_time, tick_enabled, simulation_start_time

    @staticmethod
    def utcify(dt):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def set_time(self, new_time: datetime):
        """Встановлює симульований час (UTC). Вмикає симуляцію."""
        if not isinstance(new_time, datetime):
            raise TypeError("new_time має бути об'єктом datetime")

        # Naive datetime → локальний час сервера
        if new_time.tzinfo is None:
            local_tz = tzlocal.get_localzone()
            new_time = new_time.astimezone(local_tz)

        # Конвертуємо в UTC
        new_time = new_time.astimezone(timezone.utc)

        self.user.simulated_time = new_time
        self.user.simulation_start_time = datetime.now(timezone.utc)
        self.user.tick_enabled = False  # після встановлення часу час рухається

        logger.info(f"Simulated time set to UTC: {new_time.isoformat()}")

    def now(self, tz: Optional[timezone] = timezone.utc) -> datetime:
        """Повертає поточний час з урахуванням tick і симуляції."""
        if self.user.simulated_time is None:
            current = datetime.now(timezone.utc)
        else:
            current = self.user.simulated_time
            if self.user.tick_enabled and self.user.simulation_start_time:
                sim_start_tm = self.utcify(self.user.simulation_start_time)
                logger.info(f"now: {datetime.now(timezone.utc)} simulation_start_time: {sim_start_tm}")
                delta = datetime.now(timezone.utc) - sim_start_tm
                current += delta

        current = current.astimezone(timezone.utc)

        if tz and tz != timezone.utc:
            return current.astimezone(tz)
        return current


    def toggle_tick(self, enable: bool):
        """Вмикає/вимикає рух часу."""
        if not isinstance(enable, bool):
            raise TypeError("enable має бути булевим")

        if enable and not self.user.tick_enabled:
            # Починаємо рух часу від останнього значення
            self.user.simulation_start_time = datetime.now(timezone.utc)

        if not enable and self.user.tick_enabled:
            # Зупинка: фіксуємо час на поточній позиції
            self.user.simulated_time = self.now()
            self.user.simulation_start_time = None

        self.user.tick_enabled = enable
        logger.info(f"Tick {'enabled' if enable else 'disabled'}")

    def set_real_time(self):
        """Скидає симуляцію до реального часу з урахуванням стану tick."""
        self.user.simulated_time = datetime.now(timezone.utc)
        if self.user.tick_enabled:
            # Tick ввімкнено → зберігаємо реальний час
            self.user.simulation_start_time = datetime.now(timezone.utc)
        else:
            # Tick вимкнено → фіксуємо реальний час
            self.user.simulation_start_time = None

        logger.info(f"Time reset. Tick {'enabled' if self.user.tick_enabled else 'disabled'}")

    def is_real(self) -> bool:
        return self.user.simulated_time is None

    @property
    def tick_enabled(self) -> bool:
        return self.user.tick_enabled

    def __str__(self) -> str:
        current = self.now()
        mode = "Simulated" if not self.is_real() else "Real"
        return f"{mode} time (UTC): {current.strftime('%Y-%m-%d %H:%M:%S')}"


class TimeService:
    # @staticmethod
    # def update_user_activity(user: UserSimulationState) -> None:
    #     user.last_active = datetime.now(timezone.utc)
    #     db.session.commit()

    @staticmethod
    def validate_time_format(time_str: str) -> Tuple[bool, Optional[datetime]]:
        try:
            dt = datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return True, dt
        except (ValueError, TypeError):
            return False, None