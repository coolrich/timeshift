import datetime
from logging import getLogger

import pytz
from babel.dates import format_timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone as dj_tz
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, TemplateView, ListView, UpdateView, DetailView, DeleteView

from core.models import VirtualClock
from core.services import VirtualClockController
from .exceptions import TokenRefreshTooOften
from .forms import TimeShiftUserCreationForm, UserSettingsForm
from .services import UserController

# locale.setlocale(locale.LC_TIME, "uk-UA.UTF-8")

logger = getLogger(__name__)
User = get_user_model()


class SignUpView(CreateView):
    form_class = TimeShiftUserCreationForm
    success_url = reverse_lazy("profile_dashboard")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        login(self.request, user)
        return response


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
        context["allowed_users"] = vcc.virtual_clock.allowed_users.all()
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
        logger.debug(f"accounts.views.ClockControlView.post()")
        pk = kwargs.get("pk")
        clock = get_object_or_404(self.get_queryset(), pk=pk)
        controller: VirtualClockController = VirtualClockController(clock)
        context = {"clock": clock,
                   "current_time": controller.get_time(),
                   "allowed_users": clock.allowed_users.all()}
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
        add_user = request.POST.get("add_user")
        if add_user:
            logger.debug(f"ClockControlView.post(): add_user")
            user_id = request.POST.get("add_user_id")
            logger.debug(f"ClockControlView.post(): add_user: {user_id}")
            if user_id:
                user = User.objects.filter(id=user_id).first()
                logger.debug(f"ClockControlView.post(): add_user: {user}")
                if not user:
                    m = "Користувача з таким ID не існує"
                    messages_to_user.append(m)
                    messages.error(request, m)
                    # return HttpResponse(
                    #     f"<div class='alert alert-info alert-dismissible fade show'>Юзер {user.id} не існує</div>"
                    # )
                elif clock.allowed_users.filter(id=user.id).exists():
                    m = "Користувач уже має доступ"
                    messages_to_user.append(m)
                    messages.info(request, m)
                    # return HttpResponse(
                    #     f"<div class='alert alert-info alert-dismissible fade show'>Юзер {user.id} вже має доступ</div>"
                    # )
                else:
                    m = f"Доступ надано: {user.email}"
                    messages_to_user.append(m)
                    controller.update_allowed_users({'add_users':[user_id]})
                    messages.success(request, m)
                return render(
                    request,
                    "includes/allowed_users_table.html",
                    context,
                )
        remove_user_id = request.POST.get("remove_user_id")
        if remove_user_id:
            username = request.POST.get("remove_user")
            logger.debug(f"ClockControlView.post(): remove user:"
                         f" username {username} ID {remove_user_id}")
            controller.update_allowed_users({'remove_users': [remove_user_id]})
            return render(
                request,
                "includes/allowed_users_table.html",
                context,
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


class UserSearchByIdView(LoginRequiredMixin, View):

    def get(self, request, clock_id):
        raw_id = request.GET.get("user_id", "").strip()

        if not raw_id.isdigit():
            return render(
                request,
                "includes/user_search_by_id.html"
            )

        user_id = int(raw_id)
        logger.debug(f"core.views.UserSearchByIdView.get(): looking for user id:{user_id}")

        user = (
            User.objects
            .filter(id=user_id)
            .exclude(shared_clocks__id=clock_id)
            .first()
        )
        logger.debug(f"core.views.UserSearchByIdView.get(): user: {user}")
        return render(
            request,
            "includes/user_search_by_id.html",
            {'found_user': user, 'clock_id': clock_id}
        )


