from logging import getLogger

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from accounts.services.subscription import SubscriptionService
from core.models import VirtualClock

logger = getLogger(__name__)
User = get_user_model()

class TimeShiftUserCreationForm(UserCreationForm):

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()
            SubscriptionService.assign_default_plan(user)

            subscription = getattr(user, "subscription", None)

            logger.debug(subscription)

            if subscription:
                logger.debug(subscription.plan)

                rules = subscription.plan.throttle_rules.all()

                for rule in rules:
                    logger.debug(f"Throttle rule scope: {rule.scope}")

        return user

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number')

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "timezone", 'phone_number']
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

class VirtualClockForm(forms.ModelForm):
    class Meta:
        model = VirtualClock
        fields = ['current_time', 'tick_enabled']
        labels = {
            'current_time': 'Поточний час',  # нове ім'я для поля
        }