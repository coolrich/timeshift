from django.db import models
from django.utils import timezone
import secrets

from accounts.models import TimeShiftUser
from django.contrib.auth import get_user_model

class UserSimulationState(models.Model):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE, related_name="simulation_state")
    api_token = models.CharField(max_length=64, unique=True, blank=False)
    simulated_time = models.DateTimeField(null=True, blank=True)
    simulation_start_time = models.DateTimeField(null=True, blank=True)
    tick_enabled = models.BooleanField(default=False)
    registered_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.api_token:
            while True:
                token = secrets.token_urlsafe(32)
                if not UserSimulationState.objects.filter(api_token=token).exists():
                    self.api_token = token
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Simulation state for {self.user.username}"
