from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import VirtualClock

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_virtual_clock(sender, instance, created, **kwargs):
    if created:
        VirtualClock.objects.create(user=instance)