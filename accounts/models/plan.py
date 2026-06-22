from django.db import models


class Plan(models.Model):

    class Code(models.TextChoices):
        FREE = "free", "Free"
        BASIC = "basic", "Basic"
        PRO = "pro", "Pro"
        ENTERPRISE = "enterprise", "Enterprise"

    code = models.CharField(
        max_length=20,
        choices=Code.choices,
        unique=True
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name
        # return f"Plan: name={self.name}, code={self.code}, is_active={self.is_active}"
