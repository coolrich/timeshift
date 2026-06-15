import secrets
from datetime import timedelta

import pytz
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from accounts.models import ThrottleRule
from logging import getLogger

logger = getLogger(__name__)


def generate_api_token(model, field_name="_api_token", length=32) -> str:
    """Generate a unique token, checking for collisions in the database."""
    while True:
        token = secrets.token_hex(length)
        if not model.objects.filter(**{field_name: token}).exists():
            # logger.debug(f"Generated API token: {token}")
            return token


class TimeShiftUser(AbstractUser):
    _TOKEN_REFRESH_COOLDOWN = timedelta(minutes=1)
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[MinLengthValidator(3)]
    )
    full_name = models.CharField(max_length=255, blank=True)
    _api_token = models.CharField(
        max_length=64,
        default="",  # temporarily empty, will be filled in later
        editable=False,
        unique=True,
    )
    _token_last_refreshed_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(
        max_length=50,
        choices=[(tz, tz) for tz in pytz.common_timezones],
        default="UTC",
        help_text="Часова зона користувача, наприклад Europe/Kyiv"
    )
    phone_number = PhoneNumberField(blank=False, null=False)
    max_clocks_count = models.PositiveIntegerField(default=1)
    rates = models.JSONField(default=dict, blank=True)
    rates_version = models.PositiveIntegerField(default=1)
    rates_cache = None

    def save(self, *args, **kwargs):
        if not self._api_token:
            self._api_token = generate_api_token(TimeShiftUser)
        if not kwargs.get('update_fields'):
            self.full_clean()
        super().save(*args, **kwargs)

    def refresh_token(self, *, now=None, save=True):
        from django.utils import timezone

        now = now or timezone.now()

        self._api_token = generate_api_token(self.__class__)
        self._token_last_refreshed_at = now

        if save:
            self.save(update_fields=["_api_token", "_token_last_refreshed_at"])

    def _validate_rates(self):
        if not isinstance(self.rates, dict):
            raise ValidationError("rates must be a dict")

        for scope, config in self.rates.items():

            if not isinstance(scope, str) or not scope.strip():
                raise ValidationError(f"Invalid scope key: {scope}")

            if not isinstance(config, dict):
                raise ValidationError(f"{scope}: must be a dict")

            rate = config.get("rate")

            if rate is None:
                raise ValidationError(f"{scope}: missing 'rate'")

            if not isinstance(rate, str):
                raise ValidationError(f"{scope}: rate must be string")

            rate = rate.strip()

            if not rate:
                raise ValidationError(f"{scope}: rate cannot be empty")

            self.parse_rate(rate)

    @staticmethod
    def parse_rate(rate: str) -> tuple[int, int]:
        if not isinstance(rate, str):
            raise ValidationError("Rate must be a string")

        rate = rate.strip()

        if not rate:
            raise ValidationError("Rate cannot be empty")

        parts = rate.split("/")

        if len(parts) != 2:
            raise ValidationError(f"Invalid rate format: {rate}")

        num_str, period = parts

        try:
            num = int(num_str)
        except ValueError:
            raise ValidationError(f"Invalid number in rate: {rate}")

        if num <= 0:
            raise ValidationError(f"Rate must be > 0: {rate}")

        period = period.strip()

        seconds = ThrottleRule.PERIOD_TO_SECONDS.get(period)

        if seconds is None:
            raise ValidationError(f"Invalid period in rate: {rate}")

        return num, seconds

    def get_rate(self, scope: str) -> str | None:
        rates = self.rates or {}

        config = rates.get(scope)

        if not config:
            return None

        return config.get("rate")

    @property
    def api_token(self):
        return self._api_token

    @property
    def token_last_refreshed_at(self):
        return self._token_last_refreshed_at

    @classmethod
    def get_token_refresh_cooldown(cls):
        return cls._TOKEN_REFRESH_COOLDOWN

    @property
    def rate(self):
        return f"{self.max_requests}/{self.period}"

    def __str__(self):
        return f"{self.username}"

    def clean(self):
        super().clean()
        self._validate_rates()
