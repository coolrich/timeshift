import secrets

import pytz
from django.core.validators import MinLengthValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField


def generate_api_token(model, field_name="api_token", length=32) -> str:
    """Генерує унікальний токен, перевіряючи відсутність колізій у базі."""
    while True:
        token = secrets.token_hex(length)
        if not model.objects.filter(**{field_name: token}).exists():
            return token


class TimeShiftUser(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[MinLengthValidator(3)]
    )
    full_name = models.CharField(max_length=255, blank=True)
    api_token = models.CharField(
        max_length=64,
        default="",  # тимчасово пусте, ми заповнимо нижче
        editable=False,
        unique=True,
    )
    timezone = models.CharField(
        max_length=50,
        choices=[(tz, tz) for tz in pytz.common_timezones],
        default="UTC",
        help_text="Часова зона користувача, наприклад Europe/Kyiv"
    )
    phone_number = PhoneNumberField(blank=False, null=False)
    max_clocks_count = models.PositiveIntegerField(default=3)

    def save(self, *args, **kwargs):
        if not self.api_token:
            self.api_token = generate_api_token(TimeShiftUser)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username}"
