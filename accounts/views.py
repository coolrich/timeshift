from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, ListView, UpdateView, DetailView, DeleteView, FormView
from django.views.generic.edit import FormMixin

from core.models import VirtualClock
from core.services import VirtualClockController
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
    fields = ["tick_enabled"]
    context_object_name = "clocks"

    def get_queryset(self):
        return self.request.user.virtual_clocks.all()


    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context["form"] = self.form_class()
    #     return context

class ClockDetailView(LoginRequiredMixin, DetailView):
    model = VirtualClock
    template_name = "accounts/clock_detail.html"
    context_object_name = "clock"

    def get_queryset(self):
        # тільки годинники користувача
        return self.request.user.virtual_clocks.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # vcc = VirtualClockController(self.request.user.virtual_clocks.get(id=self.kwargs["pk"]))
        vcc = VirtualClockController(self.object)
        context["current_time"] = vcc.get_time()
        logger.debug(f"Current time: {vcc.get_time()}")
        return context


class ClockCreateView(LoginRequiredMixin, CreateView):
    model = VirtualClock
    fields = ["name"]
    template_name = "accounts/clock_create.html"
    success_url = reverse_lazy("profile_clocks")

    def form_valid(self, form):
        # додаємо власника
        form.instance.user_owner = self.request.user
        logger.debug(f"Creating clock for user {self.request.user} with name {form.cleaned_data['name']}")
        try:
            return super().form_valid(form)
        except IntegrityError as e:
            logger.error(f"ClockCreateView.form_valid(): IntegrityError: {e}")
            messages.error(self.request, "Не вдалося створити годинник. Перевищено ліміт годинників.")
            return redirect("profile_clocks")

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


class ClockControlView(LoginRequiredMixin, View):
    success_url = reverse_lazy("profile_clocks")

    def get_queryset(self):
        # дозволяємо контролювати лише свої годинники
        return self.request.user.virtual_clocks.all()

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        clock = get_object_or_404(self.get_queryset(), pk=pk)

        controller = VirtualClockController(clock)
        controller.toggle_tick()
        controller.save()

        return redirect(self.success_url)


    # def get(self, request, *args, **kwargs):
    #     # vc = self.request.user.virtual_clocks.get(id=self.kwargs["pk"])
    #     # vcc = VirtualClockController(vc)
    #     logger.debug(f"ClockControlView.post(): request.POST: {self.request.GET}")
    #     self.request.GET['tick_enabled'] = bytes(not self.request.GET['tick_enabled'])
    #     # vcc.toggle_tick(enabled=not self.request.POST['tick_enabled'])
    #     # vcc.save()
    #     # logger.debug(f"ClockControlView.post(): tick_enabled: ")
    #     return super().post(request, *args, **kwargs)