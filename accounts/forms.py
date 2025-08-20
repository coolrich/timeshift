from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import TimeShiftUser
from django.contrib.auth import get_user_model

User = get_user_model()

class TimeShiftUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email')