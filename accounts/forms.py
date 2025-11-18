from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from logging import getLogger

logger = getLogger(__name__)
User = get_user_model()

class TimeShiftUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email')

User = get_user_model()

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]  # можеш розширити
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }
