import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class VirtualClock(models.Model):
    user_owner = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="virtual_clocks"
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    # api_token = models.CharField(max_length=64, unique=True, editable=False, null=False)
    allowed_users = models.ManyToManyField(
        get_user_model(), related_name="shared_clocks", blank=True
    )

    current_time = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(default=timezone.now)
    speed = models.FloatField(
        default=1.0,
        validators=[
            MinValueValidator(0.01),
            MaxValueValidator(100.0),
        ],
    )
    tick_enabled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.user_owner_id and self.allowed_users.filter(
                pk=self.user_owner_id
        ).exists():
            raise ValidationError("Owner cannot be in allowed_users.")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"VirtualClock '{self.name}' of {self.user_owner.username} with id: {self.id}"
