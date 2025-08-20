from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeShiftUser(AbstractUser):
    full_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.username
