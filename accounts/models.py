import secrets
from datetime import timedelta

import pytz
from django.core.validators import MinLengthValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField


def generate_api_token(model, field_name="_api_token", length=32) -> str:
    """Генерує унікальний токен, перевіряючи відсутність колізій у базі."""
    while True:
        token = secrets.token_hex(length)
        if not model.objects.filter(**{field_name: token}).exists():
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
        default="",  # тимчасово пусте, ми заповнимо нижче
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
    max_clocks_count = models.PositiveIntegerField(default=3)

    def save(self, *args, **kwargs):
        if not self._api_token:
            self._api_token = generate_api_token(TimeShiftUser)
        super().save(*args, **kwargs)

    def refresh_token(self, *, now=None, save=True):
        from django.utils import timezone

        now = now or timezone.now()

        self._api_token = generate_api_token(self.__class__)
        self._token_last_refreshed_at = now

        if save:
            self.save(update_fields=["_api_token", "_token_last_refreshed_at"])

    @property
    def api_token(self):
        return self._api_token

    @property
    def token_last_refreshed_at(self):
        return self._token_last_refreshed_at

    @classmethod
    def get_token_refresh_cooldown(cls):
        return cls._TOKEN_REFRESH_COOLDOWN


    def __str__(self):
        return f"{self.username}"
