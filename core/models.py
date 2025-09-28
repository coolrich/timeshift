import uuid
import secrets

from django.db import models, IntegrityError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

class VirtualClock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    private_id = models.PositiveIntegerField(unique=True, editable=False, default=1)

    user_owner = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="virtual_clocks"
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    api_token = models.CharField(max_length=64, unique=True, editable=False)
    allowed_users = models.ManyToManyField(
        get_user_model(), related_name="shared_clocks", blank=True
    )

    current_time = models.DateTimeField(default=timezone.now)
    tick_enabled = models.BooleanField(default=False)
    last_updated = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk and self.allowed_users.filter(pk=self.user_owner.pk).exists():
            raise IntegrityError("Owner cannot be in allowed_users.")

        if not self.api_token:
            while True:
                token = secrets.token_urlsafe(32)
                if not VirtualClock.objects.filter(api_token=token).exists():
                    self.api_token = token
                    logger.info(f"core.models.VirtualClock.save(): api_token: {self.api_token}")
                    break

        last = VirtualClock.objects.all().order_by("-private_id").first()
        logger.info(f"core.models.VirtualClock.save(): last private_id: {last.private_id}")
        logger.info(f"core.models.VirtualClock.save(): self.private_id: {self.private_id}")
        if not self.private_id or self.private_id <= last.private_id:
            # last = VirtualClock.objects.all().order_by("-public_id").first()
            self.private_id = 1 if not last else int(last.private_id) + 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["private_id"]

    def __str__(self):
        return f"VirtualClock '{self.name or self.id}' of {self.user_owner.username}"


# Сигнал для відлову .add() в allowed_users
@receiver(m2m_changed, sender=VirtualClock.allowed_users.through)
def prevent_owner_in_allowed(sender, instance, action, pk_set, **kwargs):
    if action == "pre_add":
        if instance.user_owner_id in pk_set:
            raise IntegrityError("Owner cannot be added to allowed_users.")
