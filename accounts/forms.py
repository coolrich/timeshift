from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from logging import getLogger

from core.models import VirtualClock

logger = getLogger(__name__)
User = get_user_model()

class TimeShiftUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number')

User = get_user_model()

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
        fields = ['current_time']
        labels = {
            'current_time': 'Поточний час',  # нове ім'я для поля
        }