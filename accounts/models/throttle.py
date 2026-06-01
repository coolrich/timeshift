from django.db import models
from django.db.models import UniqueConstraint


class ThrottleRule(models.Model):
    class Period(models.TextChoices):
        SECOND = "s", "Second"
        MINUTE = "m", "Minute"
        HOUR = "h", "Hour"
        DAY = "d", "Day"

    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"
        CLOCKS_CREATE = "clock_create", "Clock Create"
        TOKEN_REFRESH = "token_refresh", "Token Refresh"
        CLOCK_CONTROL = "clock_control", "Clock Control"
        PROFILE_SETTINGS = "profile_settings", "Profile Settings"
        CLOCK_DELETE = "clock_delete", "Clock Delete"
        # SIGN_UP = "sign_up", "Sign Up"

    plan = models.ForeignKey(
        'accounts.Plan',
        on_delete=models.CASCADE,
        related_name="throttle_rules"
    )

    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.GLOBAL
    )

    max_requests = models.PositiveIntegerField(default=60)
    period = models.CharField(
        max_length=1,
        choices=Period.choices,
        default=Period.MINUTE
    )

    PERIOD_TO_SECONDS = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    def window_seconds(self) -> int:
        return self.PERIOD_TO_SECONDS[self.period]

    class Meta:
        # unique_together = ("plan", "scope")
        constraints = [
            models.constraints.CheckConstraint(
                condition=models.Q(max_requests__gt=0),
                name="requests_must_be_positive"
            ),
            UniqueConstraint(fields=["plan", "scope"], name="unique_plan_scope")
        ]

    @property
    def rate(self) -> str:
        return f"{self.max_requests}/{self.period}"

    def __str__(self) -> str:
        return f"ThrottleRule: plan=({self.plan}), scope=({self.scope}), max_requests=({self.max_requests}), period=({self.period})"
