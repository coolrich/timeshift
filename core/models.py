import inspect
import logging
import warnings

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, IntegrityError
from django.utils import timezone

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

    def __init__(self, *args, **kwargs):
        # Перевіряємо стек викликів
        module_name = None
        for frame in inspect.stack():
            module_name = frame.frame.f_globals.get("__name__", "")
            if module_name.startswith(("core.services", "threading")):
                break
        else:
            warnings.warn(
                f"VirtualClock використовується напряму в модулі {module_name}. Використовуйте VirtualClockController.",
                stacklevel=2
            )
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.pk and self.allowed_users.filter(pk=self.user_owner.pk).exists():
            raise IntegrityError("Owner cannot be in allowed_users.")

        if not self.pk and self.user_owner.virtual_clocks.count() >= self.user_owner.max_clocks_count:
            for clock in self.user_owner.virtual_clocks.order_by("-created_at").all():
                if self.user_owner.virtual_clocks.count() <= self.user_owner.max_clocks_count:
                    break
                clock.delete()
            raise IntegrityError("User has reached the maximum number of clocks.")

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
