from datetime import timezone, timedelta, datetime
from logging import getLogger
from typing import Any, Type

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils import timezone
from ninja.errors import HttpError

from accounts.models import TimeShiftUser
from .models import VirtualClock

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
        self._virtual_clock: VirtualClock = virtual_clock

    @property
    def virtual_clock(self) -> VirtualClock:
        """
        Get the virtual clock instance.

        Returns:
            VirtualClock: The virtual clock instance being controlled
        """
        return self._virtual_clock

    def _current_time(self) -> timedelta | datetime | Any:
        """
        Calculate the current virtual time in memory without saving to the database.
        
        Returns:
            Union[timedelta, datetime, Any]: The current virtual time. If the clock is ticking,
            returns the calculated UTC time based on the last update. Otherwise, returns the static time.
        """
        if self._virtual_clock.tick_enabled:
            now = timezone.now()
            delta = now - self._virtual_clock.last_updated
            return self._virtual_clock.current_time + delta
        return self._virtual_clock.current_time

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
        return self._virtual_clock.user_owner

    def set_time(self, new_time: datetime, save: bool=True) -> Type['VirtualClockController']:
        """
        Set the virtual clock to a specific time and stop the tick.

        Args:
            new_time (datetime): The new time to set for the virtual clock.
            save (bool): automatically save to database if True
        Returns:
            VirtualClock: The updated VirtualClock instance.
            Note: Changes are in memory only, call save() to persist to database.
        """
        now = timezone.now()
        self._virtual_clock.current_time = new_time
        self._virtual_clock.last_updated = now
        self._virtual_clock.tick_enabled = False
        if save:
            self.save()
        return self

    def set_real_time(self, save: bool=True) -> Type['VirtualClockController']:
        """
        Set the virtual clock to the current real time and stop the tick.

        Args:
            save (bool): automatically save to database if True
        Returns:
            VirtualClock: The updated VirtualClock instance.
        """
        now = timezone.now()
        self._virtual_clock.current_time = now
        self._virtual_clock.last_updated = now
        self._virtual_clock.tick_enabled = False
        if save:
            self.save()
        return self



    def toggle_tick(self, enabled: bool = None, save: bool=True) -> Type['VirtualClockController']:
        """
        Toggle or set the tick status of the virtual clock.
        
        Args:
            enabled (bool, optional): If provided, sets the tick to this value. If None, toggles the current state.
            save (bool): automatically save to database if True

                                    
        Returns:
            VirtualClock: The updated VirtualClock instance.
            Note: Changes are in memory only, call save() to persist to database.
        """
        now = timezone.now()
        self._virtual_clock.current_time = self._current_time()
        self._virtual_clock.last_updated = now
        self._virtual_clock.tick_enabled = not self._virtual_clock.tick_enabled if enabled is None else enabled
        if save:
            self.save()
        return self

    def set_clock_name(self, new_name: str, save: bool=True) -> Type['VirtualClockController']:
        """
        Повертає оновлений об'єкт VirtualClockController.

        Args:
            save (bool): automatically save to database if True

        """
        if len(new_name) > 255:
            raise HttpError(400, "Name is too long (max 255)")
        logger.info(f"core.services.VirtualClockController.set_clock_name(): new_name: {new_name}")
        self._virtual_clock.name = new_name
        if save:
            self.save()
        return self

    def save(self) -> Type['VirtualClockController']:
        """
        Save the current state of the virtual clock to the database.
        
        Returns:
            VirtualClock: The saved VirtualClock instance.
        """
        self._virtual_clock.save()
        return self

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


    def delete(self, user: User) -> Type['VirtualClockController']:
        """
        Delete the specified clock instance.
        
        Args:
            user (User): The user who owns the clock to delete.
        """
        if self._virtual_clock.user_owner != user:
            raise HttpError(403, "You are not the owner of this clock")
        self._virtual_clock.delete()
        return self

    @property
    def clock_name(self) -> str:
        return self._virtual_clock.name

    @property
    def tick_status(self) -> bool:
        """
        Get the current tick status of the virtual clock.
        
        Returns:
            bool: True if the clock is ticking, False otherwise
        """
        return self._virtual_clock.tick_enabled

    def update_allowed_users(self, payload: dict, save: bool=True) -> Type['VirtualClockController']:
        """
        Update the list of users who have access to this virtual clock.
        
        The payload can contain one or more of the following keys:
        - "allowed_users": List of user IDs to completely replace the current access list
        - "add_users": List of user IDs to add to the current access list
        - "remove_users": List of user IDs to remove from the current access list
        
        Args:
            payload (dict): Dictionary containing update instructions.
            save (bool): automatically save to database if True

        Note:
            Changes are in memory only, call save() to persist to database.
        """
        # Full update of allowed users
        # if 'allowed_users' in payload:
        #     self._virtual_clock.allowed_users.set(payload['allowed_users'])
            
        # Add users to existing allowed users
        # if 'add_users' in payload and payload['add_users']:
        #     self._virtual_clock.allowed_users.add(*payload['add_users'])

        # Remove users from allowed users
        # if 'remove_users' in payload and payload['remove_users']:
        #     self._virtual_clock.allowed_users.remove(*payload['remove_users'])

        # Full update of allowed users
        if "allowed_users" in payload and payload["allowed_users"]:
            users = TimeShiftUser.objects.filter(id__in=payload["allowed_users"])
            self._virtual_clock.allowed_users.set(users)

        # Add users to existing allowed users
        if "add_users" in payload and payload["add_users"]:
            users = TimeShiftUser.objects.filter(id__in=payload["add_users"])
            self._virtual_clock.allowed_users.add(*users)

        # Removing users
        if "remove_users" in payload and payload["remove_users"]:
            users = TimeShiftUser.objects.filter(id__in=payload["remove_users"])
            self._virtual_clock.allowed_users.remove(*users)

        if save:
            self.save()

        return self
