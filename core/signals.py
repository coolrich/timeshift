from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import VirtualClock

User = get_user_model()

# @receiver(post_save, sender=User)
# def create_user_virtual_clock(sender, instance, created, **kwargs):
#     if created:
#         new_public_id = VirtualClock.objects.all().order_by("-public_id").first().public_id + 1
#         VirtualClock.objects.create(user_owner=instance, public_id=new_public_id)

# Сигнал для відлову .add() в allowed_users
@receiver(m2m_changed, sender=VirtualClock.allowed_users.through)
def prevent_owner_in_allowed(sender, instance, action, pk_set, **kwargs):
    if action == "pre_add":
        if instance.user_owner_id in pk_set:
            raise IntegrityError("Owner cannot be added to allowed_users.")

# @receiver(post_save, sender=VirtualClock)
# def prevent_current_time_wrong_format(sender, instance, **kwargs):
#     try:
#         datetime.datetime.fromisoformat(instance.current_time)
#     except ValueError:
#         raise IntegrityError("Current time must be in ISO format.")
