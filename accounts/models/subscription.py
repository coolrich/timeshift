from django.db import models

from django_project import settings


class UserSubscription(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription"
    )

    plan = models.ForeignKey(
        'accounts.Plan',
        on_delete=models.PROTECT
    )

    started_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Підписка"
        verbose_name_plural = "Підписки"

        constraints = [models.UniqueConstraint(fields=["user"], name="unique_user_subscription")]

    def __str__(self) -> str:
        return f"UserSubscription: user=({self.user}), plan=({self.plan}), started_at=({self.started_at}), expires_at=({self.expires_at})"