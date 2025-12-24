import datetime
from logging import getLogger

import pytz
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone as dj_tz
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, TemplateView, ListView, UpdateView, DetailView, DeleteView
from django.views.generic.edit import ModelFormMixin

from core.models import VirtualClock
from core.services import VirtualClockController
from .exceptions import TokenRefreshTooOften
from .forms import TimeShiftUserCreationForm, UserSettingsForm, VirtualClockForm
from .services import UserController
from babel.dates import format_date, format_timedelta

# locale.setlocale(locale.LC_TIME, "uk-UA.UTF-8")

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
    fields = ["current_time", "tick_enabled"]

    # form_class = VirtualClockForm

    def get_queryset(self):
        # тільки годинники користувача
        return self.request.user.virtual_clocks.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # vcc = VirtualClockController(self.request.user.virtual_clocks.get(id=self.kwargs["pk"]))
        vcc = VirtualClockController(self.object)
        context["current_time"] = vcc.get_time()
        # context['tick_enabled'] = vcc.tick_status
        user_tz = self.request.user.timezone
        dj_tz.activate(user_tz)
        logger.debug(f"Current time: {vcc.get_iso_time()}")
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
        messages.success(self.request, "Налаштування збережено.")
        return response


class ClockStateControlView(LoginRequiredMixin, View):
    # success_url = reverse_lazy("profile_clocks")

    def get_queryset(self):
        # дозволяємо контролювати лише свої годинники
        return self.request.user.virtual_clocks.all()

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        clock = get_object_or_404(self.get_queryset(), pk=pk)

        controller = VirtualClockController(clock)
        name = request.POST.get('name')
        if name:
            controller.set_clock_name(name)
        else:
            controller.toggle_tick()
        # controller.save()
        # logger.error(f"ClockCreateView.form_valid(): TypeError: {e}")
        # messages.error(self.request, "Не вдалося встановити час. Перевірте правильність формату ISO 8601")
        # logger.debug(f"ClockStateControlView.post(): clock_id={kwargs['pk']}")
        referrer = request.META.get("HTTP_REFERER")
        if referrer:
            return redirect(referrer)  # , kwargs={"pk": kwargs['pk']})
        else:
            return redirect(reverse('home'))


class ClockTimeControlView(LoginRequiredMixin, View):
    success_url = reverse_lazy("profile_clocks")

    def get_queryset(self):
        # дозволяємо контролювати лише свої годинники
        return self.request.user.virtual_clocks.all()

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        clock = get_object_or_404(self.get_queryset(), pk=pk)
        controller = VirtualClockController(clock)
        logger.debug(f"ClockStateControlView.post(): current_time={request.POST['current_time']}")
        try:
            tz = pytz.timezone(self.request.user.timezone)
            dt_naive = datetime.datetime.strptime(
                request.POST['current_time'],
                "%d.%m.%Y %H:%M:%S"
            )
            # Робимо tz-aware дату
            dt_user = tz.localize(dt_naive)
            # dt_iso = dt_user.isoformat()
        except (ValueError, pytz.UnknownTimeZoneError) as e:
            logger.error(f"ClockTimeControlView.post(): ValueError: {e}")
            messages.error(self.request, "Не вдалося встановити час. Перевірте правильність формату ISO 8601")
            return redirect(reverse('clock_detail', kwargs={"pk": kwargs['pk']}))
        # set_time automatically save state to DB
        controller.set_time(dt_user)
        # controller.save()
        return redirect(reverse('clock_detail', kwargs={"pk": kwargs['pk']}))


class UserTokenUpdateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        logger.debug(f"UserTokenUpdateView(): post(): old token\n{request.user.api_token}")
        try:
            user = UserController(self.request.user).update_token()
            logger.debug(f"UserTokenUpdateView(): post(): new token generated:\n{user.api_token}")
        except TokenRefreshTooOften as e:
            logger.debug(f"UserTokenUpdateView.post(): token update error")
            total_seconds = User.get_token_refresh_cooldown().total_seconds()
            t = format_timedelta(total_seconds, locale='uk', format='short')
            # logger.debug(f"UserTokenUpdateView.post(): help(TOKEN_REFRESH_COOLDOWN):{help(User.TOKEN_REFRESH_COOLDOWN)}")
            messages.error(
                request,
                f"Токен можна оновлювати раз на {t}. Спробуй через {e.retry_after} с."
            )
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return redirect(referer)
        else:
            return redirect(reverse('home'))


class ClockControlView(LoginRequiredMixin, View):
    def get_queryset(self):
        return self.request.user.virtual_clocks.all()

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        clock = get_object_or_404(self.get_queryset(), pk=pk)
        controller: VirtualClockController = VirtualClockController(clock)
        context = {"clock": clock, "current_time": controller.get_time()}
        messages_to_user = []

        # --- Назва ---
        name = request.POST.get("clock_name")
        if name and name != controller.clock_name:
            controller.set_clock_name(name, save=False)
            messages_to_user.append(f"Назва годинника змінена на {name}")

        # --- Тікання ---
        element = request.POST.get("tick_enabled")
        tick_enabled = element == "on"
        if element and tick_enabled != controller.tick_status:
            logger.debug(f"ClockControlView.post(): if tick_enabled != controller.tick_status")
            controller.toggle_tick(save=False)  # або окремий метод set_tick(tick_enabled)
            state = "увімкнено" if tick_enabled else "вимкнено"
            messages_to_user.append(f"Тікання годинника {state}")
        if request.POST.get('toggle_tick'):
            logger.debug(f"ClockControlView.post(): if request.POST.get('toggle_tick')")
            controller.toggle_tick()
            state = "увімкнено" if controller.tick_status else "вимкнено"
            messages_to_user.append(f"Тікання годинника {state}")

        # --- Час ---
        current_time = request.POST.get("current_time")
        if current_time:
            try:
                tz = pytz.timezone(request.user.timezone)
                dt_naive = datetime.datetime.fromisoformat(current_time)
                dt_user = tz.localize(dt_naive)
                controller.set_time(dt_user, save=False)
                messages_to_user.append(
                    f"Час годинника оновлено на {dt_user}"
                )
            except (ValueError, pytz.UnknownTimeZoneError) as e:
                messages.error(
                    request,
                    "Не вдалося встановити час. Перевірте правильність формату"
                )
                return render(
                    request,
                    "accounts/clock_detail.html",
                    context,
                    status=400,
                )
                # --- Відправка повідомлень ---
        for msg in messages_to_user:
            messages.success(request, msg)
            logger.info(f"[ClockControlView] Clock(pk={pk}): {msg}")
        controller.save()

        next_url = request.POST.get("next")

        if not next_url or not url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
        ):
            next_url = reverse("home")

        return redirect(next_url)