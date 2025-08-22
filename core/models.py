from django.db import models
from django.utils import timezone
import secrets
from django.contrib.auth import get_user_model

class VirtualClock(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name="virtual_clock")
    name = models.CharField(max_length=255, blank=True, null=True)
    api_token = models.CharField(max_length=64, unique=True, editable=False)

    current_time = models.DateTimeField(default=timezone.now)
    tick_enabled = models.BooleanField(default=False)
    last_updated = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    #  В майбутньому можна перемістити в менеджер для моделі
    def save(self, *args, **kwargs):
        if not self.api_token:
            while True:
                token = secrets.token_urlsafe(32)
                if not VirtualClock.objects.filter(api_token=token).exists():
                    self.api_token = token
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Simulation state of {self.user.username} (id={self.user.id})"