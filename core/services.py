from datetime import timezone
from django.utils import timezone
from .models import VirtualClock
from logging import getLogger

logger = getLogger(__name__)


class TimeShiftController:
    def __init__(self, virtual_clock: VirtualClock):
        self.virtual_clock: VirtualClock = virtual_clock

    def _current_time(self):
        """Обчислює поточний час у пам'яті без запису в БД"""
        if self.virtual_clock.tick_enabled:
            now = timezone.now()
            delta = now - self.virtual_clock.last_updated
            return self.virtual_clock.current_time + delta
        return self.virtual_clock.current_time

    def get_time(self):
        """Повертає поточний час і стан тіку, без save()"""
        return self._current_time().isoformat()


    def set_real(self):
        """Встановлює реальний час і зупиняє тік, зміни у пам'яті"""
        now = timezone.now()
        self.virtual_clock.current_time = now
        self.virtual_clock.last_updated = now
        self.virtual_clock.tick_enabled = False
        return self.virtual_clock  # save робить commit() окремо

    def set_time(self, new_time):
        """Встановлює довільний час і зупиняє тік"""
        now = timezone.now()
        self.virtual_clock.current_time = new_time
        self.virtual_clock.last_updated = now
        self.virtual_clock.tick_enabled = False
        return self.virtual_clock

    def toggle_tick(self, enabled: bool = None):
        """Перемикає tick_enabled, зміни у пам'яті"""
        now = timezone.now()
        self.virtual_clock.current_time = self._current_time()
        self.virtual_clock.last_updated = now
        self.virtual_clock.tick_enabled = not self.virtual_clock.tick_enabled if not enabled else enabled
        return self.virtual_clock

    @property
    def tick_status(self):
        return self.virtual_clock.tick_enabled

    def commit(self):
        """Явний запис змін у базу"""
        self.virtual_clock.save()
        return self.virtual_clock
