import secrets
from django.db import models
from django.contrib.auth.models import AbstractUser

def generate_api_token(model, field_name="api_token", length=32):
    """Генерує унікальний токен, перевіряючи відсутність колізій у базі."""
    while True:
        token = secrets.token_hex(length)
        if not model.objects.filter(**{field_name: token}).exists():
            return token

class TimeShiftUser(AbstractUser):
    api_token = models.CharField(
        max_length=64,
        default="",  # тимчасово пусте, ми заповнимо нижче
        editable=False,
        unique=True,
    )
    full_name = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if not self.api_token:
            self.api_token = generate_api_token(TimeShiftUser)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
