from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .forms import TimeShiftUserCreationForm

class SignUpView(CreateView):
    form_class = TimeShiftUserCreationForm
    success_url = reverse_lazy("profile")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        login(self.request, user)
        return response

class ProfileView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("login")
    template_name = "accounts/profile.html"