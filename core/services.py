from datetime import timezone, timedelta, datetime
from typing import Any

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
    """
    Controller class for managing virtual clock operations.
    Handles time manipulation, tick control, and clock configuration.
    """
    def __init__(self, virtual_clock: VirtualClock):
        """
        Initialize the VirtualClockController with a VirtualClock instance.
        
        Args:
            virtual_clock (VirtualClock): The virtual clock instance to control
        """
        self.virtual_clock: VirtualClock = virtual_clock

    def _current_time(self) -> timedelta | datetime | Any:
        """
        Calculate the current virtual time in memory without saving to the database.
        
        Returns:
            Union[timedelta, datetime, Any]: The current virtual time. If the clock is ticking,
            returns the calculated UTC time based on the last update. Otherwise, returns the static time.
        """
        if self.virtual_clock.tick_enabled:
            now = timezone.now()
            delta = now - self.virtual_clock.last_updated
            return self.virtual_clock.current_time + delta
        return self.virtual_clock.current_time

    def get_iso_time(self) -> str:
        """
        Get the current virtual time in ISO format.
        
        Returns:
            str: The current virtual UTC time as an ISO formatted string.
            The time is calculated based on the current state of the clock.
        """
        return self._current_time().isoformat()

    def get_time(self) -> datetime:
        """
        Get the current virtual time.

        Returns:
            datetime: The current virtual UTC time as a datetime object.
            The time is calculated based on the current state of the clock.
        """
        return self._current_time()

    def get_user_owner(self) -> User:
        """
        Get the owner of the virtual clock.
        
        Returns:
            User: The user who owns this virtual clock
        """
        return self.virtual_clock.user_owner

    def set_time(self, new_time: datetime) -> VirtualClock:
        """
        Set the virtual clock to a specific time and stop the tick.

        Args:
            new_time (datetime): The new time to set for the virtual clock.

        Returns:
            VirtualClock: The updated VirtualClock instance.
            Note: Changes are in memory only, call save() to persist to database.
        """
        now = timezone.now()
        self.virtual_clock.current_time = new_time
        self.virtual_clock.last_updated = now
        self.virtual_clock.tick_enabled = False
        return self.virtual_clock

    def set_real_time(self) -> VirtualClock:
        """
        Set the virtual clock to the current real time and stop the tick.
        
        Returns:
            VirtualClock: The updated VirtualClock instance.
            Note: Changes are in memory only, call save() to persist to database.
        """
        now = timezone.now()
        self.virtual_clock.current_time = now
        self.virtual_clock.last_updated = now
        self.virtual_clock.tick_enabled = False
        return self.virtual_clock



    def toggle_tick(self, enabled: bool = None) -> VirtualClock:
        """
        Toggle or set the tick status of the virtual clock.
        
        Args:
            enabled (bool, optional): If provided, sets the tick to this value.
                                    If None, toggles the current state.
                                    
        Returns:
            VirtualClock: The updated VirtualClock instance.
            Note: Changes are in memory only, call save() to persist to database.
        """
        now = timezone.now()
        self.virtual_clock.current_time = self._current_time()
        self.virtual_clock.last_updated = now
        self.virtual_clock.tick_enabled = not self.virtual_clock.tick_enabled if enabled is None else enabled
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

    def save(self) -> VirtualClock:
        """
        Save the current state of the virtual clock to the database.
        
        Returns:
            VirtualClock: The saved VirtualClock instance.
        """
        self.virtual_clock.save()
        return self.virtual_clock

    # retrieve a list of clocks
    @staticmethod
    def list_clocks(user: User) -> QuerySet[VirtualClock]:
        """
        Get all virtual clocks visible to the specified user.
        
        Args:
            user (User): The user whose clocks to retrieve.
            
        Returns:
            QuerySet[VirtualClock]: A queryset containing all virtual clocks
            owned by the user or shared with the user.
        """
        return VirtualClock.objects.filter(user_owner=user) | user.shared_clocks.all()

    @staticmethod
    def delete_clock(clock_instance) -> None:
        """
        Delete the specified clock instance.
        
        Args:
            clock_instance: The VirtualClock instance to delete
        """
        clock_instance.delete()

    @property
    def tick_status(self) -> bool:
        """
        Get the current tick status of the virtual clock.
        
        Returns:
            bool: True if the clock is ticking, False otherwise
        """
        return self.virtual_clock.tick_enabled

    def update_allowed_users(self, payload: dict) -> None:
        """
        Update the list of users who have access to this virtual clock.
        
        The payload can contain one or more of the following keys:
        - "allowed_users": List of user IDs to completely replace the current access list
        - "add_users": List of user IDs to add to the current access list
        - "remove_users": List of user IDs to remove from the current access list
        
        Args:
            payload (dict): Dictionary containing update instructions.
            
        Note:
            Changes are in memory only, call save() to persist to database.
        """
        # Full update of allowed users
        if 'allowed_users' in payload:
            self.virtual_clock.allowed_users.set(payload['allowed_users'])
            
        # Add users to existing allowed users
        if 'add_users' in payload and payload['add_users']:
            self.virtual_clock.allowed_users.add(*payload['add_users'])
            
        # Remove users from allowed users
        if 'remove_users' in payload and payload['remove_users']:
            self.virtual_clock.allowed_users.remove(*payload['remove_users'])
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
