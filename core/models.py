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
    id = models.PositiveIntegerField(primary_key=True, unique=True, editable=False, null=False)
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
    tick_enabled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk and self.allowed_users.filter(pk=self.user_owner.pk).exists():
            raise IntegrityError("Owner cannot be in allowed_users.")

        if self.user_owner.virtual_clocks.count() > self.user_owner.max_clocks_count:
            for clock in self.user_owner.virtual_clocks.order_by("-created_at").all():
                if self.user_owner.virtual_clocks.count() <= self.user_owner.max_clocks_count:
                    break
                clock.delete()
            raise IntegrityError("User has reached the maximum number of clocks.")

        # if not self.api_token:
        #     while True:
        #         token = secrets.token_urlsafe(32)
        #         if not VirtualClock.objects.filter(api_token=token).exists():
        #             self.api_token = token
        #             logger.info(f"core.models.VirtualClock.save(): new api_token created: {self.api_token}")
        #             break

        last = VirtualClock.objects.all().order_by("-id").first()
        logger.debug(f"core.models.VirtualClock.save(): last: {last}")
        if not last:
            logger.debug(f"core.models.VirtualClock.save(): created first clock")
            self.id = 1
        else:
            logger.debug(f"core.models.VirtualClock.save(): self.id is {self.id}")
            if not self.id:
                logger.debug(f"core.models.VirtualClock.save(): initiated id: {int(last.id) + 1}")
                self.id = int(last.id) + 1
        logger.debug(f"core.models.VirtualClock.save(): self.id is {self.id} | name: {self.name} | tick_enabled: {self.tick_enabled}")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"VirtualClock '{self.name}' of {self.user_owner.username} with id: {self.id}"
