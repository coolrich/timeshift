from datetime import timezone

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja.errors import HttpError

from accounts.models import TimeShiftUser
from .models import VirtualClock
from logging import getLogger
User = get_user_model()

logger = getLogger(__name__)


class VirtualClockController:
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

    def get_user_owner(self):
        return self.virtual_clock.user_owner

    def set_real_time(self):
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

    def set_clock_name(self, new_name: str):
        """
        Змінює назву годинника у пам'яті (без запису в БД).
        Повертає оновлений об'єкт VirtualClock.
        """
        if len(new_name) > 255:
            raise HttpError(400, "Name is too long (max 255)")
        logger.info(f"core.services.VirtualClockController.set_clock_name(): new_name: {new_name}")
        self.virtual_clock.name = new_name
        return self.virtual_clock

    def save(self):
        """Явний запис змін у базу"""
        self.virtual_clock.save()
        return self.virtual_clock

    # retrieve a list of clocks
    @staticmethod
    def list_clocks(user: User) -> QuerySet[VirtualClock]:
        """Returns list of clocks of specified user"""
        # return VirtualClock.objects.all(user)
        return VirtualClock.objects.filter(user_owner=user) | user.shared_clocks.all()
        # return self.virtual_clock.objects.all()

    @staticmethod
    def delete_clock(self, user, clock_id):
        self.virtual_clock.delete()

    @property
    def tick_status(self):
        return self.virtual_clock.tick_enabled

    def update_allowed_users(self, payload: dict):
        """
        payload може містити:
          - "allowed_users" → повний список id користувачів (replace)
          - "add_users" → список id для додавання
          - "remove_users" → список id для видалення
        """
        # Повне оновлення
        if "allowed_users" in payload and payload["allowed_users"]:
            users = TimeShiftUser.objects.filter(id__in=payload["allowed_users"])
            self.virtual_clock.allowed_users.set(users)

        # Додавання
        if "add_users" in payload and payload["add_users"]:
            users = TimeShiftUser.objects.filter(id__in=payload["add_users"])
            self.virtual_clock.allowed_users.add(*users)

        # Видалення
        if "remove_users" in payload and payload["remove_users"]:
            users = TimeShiftUser.objects.filter(id__in=payload["remove_users"])
            self.virtual_clock.allowed_users.remove(*users)

        return self.virtual_clock
