from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, ListView, UpdateView, DetailView, DeleteView

from core.models import VirtualClock
from .forms import TimeShiftUserCreationForm, UserSettingsForm
from django.contrib.auth import get_user_model
from logging import getLogger

logger = getLogger(__name__)

class SignUpView(CreateView):
    form_class = TimeShiftUserCreationForm
    success_url = reverse_lazy("profile_dashboard")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        login(self.request, user)
        return response

# class ProfileView(LoginRequiredMixin, TemplateView):
#     model = get_user_model()
#     template_name = "accounts/profile.html"
#     login_url = reverse_lazy("login")
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['virtual_clocks'] = self.request.user.virtual_clocks.all()
#         return context

User = get_user_model()

# 🧭 1. Головна сторінка (дашборд)
class ProfileDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"
    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["total_clocks"] = user.virtual_clocks.count()
        context["latest_clock"] = (
            user.virtual_clocks.order_by("-created_at").first()
            if hasattr(user, "virtual_clocks")
            else None
        )
        return context


# 🔑 2. Сторінка токенів
class ProfileTokensView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/tokens.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        context["virtual_clocks"] = getattr(self.request.user, "virtual_clocks", None)
        return context


# ⏱️ 3. Список віртуальних годинників
class ProfileClocksView(LoginRequiredMixin, ListView):
    model = VirtualClock
    template_name = "accounts/clocks.html"
    context_object_name = "clocks"

    def get_queryset(self):
        return self.request.user.virtual_clocks.all()

class ClockDetailView(LoginRequiredMixin, DetailView):
    model = VirtualClock
    template_name = "accounts/clock_detail.html"
    context_object_name = "clock"

    def get_queryset(self):
        # тільки годинники користувача
        return self.request.user.virtual_clocks.all()


class ClockCreateView(LoginRequiredMixin, CreateView):
    model = VirtualClock
    fields = ["name"]
    template_name = "accounts/clock_create.html"
    success_url = reverse_lazy("profile_clocks")

    def form_valid(self, form):
        # додаємо власника
        form.instance.user_owner = self.request.user
        logger.debug(f"Creating clock for user {self.request.user} with name {form.cleaned_data['name']}")
        return super().form_valid(form)

class ClockDeleteView(LoginRequiredMixin, DeleteView):
    model = VirtualClock
    template_name = "accounts/clock_confirm_delete.html"
    success_url = reverse_lazy("profile_clocks")

    def get_queryset(self):
        # дозволяємо видаляти лише свої годинники
        return self.request.user.virtual_clocks.all()

# ⚙️ 4. Налаштування користувача
class ProfileSettingsView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserSettingsForm
    template_name = "accounts/settings.html"
    success_url = reverse_lazy("profile_settings")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        # можна додати повідомлення: messages.success(self.request, "Налаштування збережено.")
        return response
