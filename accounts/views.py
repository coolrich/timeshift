import datetime
import re
from collections import defaultdict
from logging import getLogger
from typing import Any

import pytz
from babel.dates import format_timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone as dj_tz
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, TemplateView, ListView, UpdateView, DetailView, DeleteView

from accounts.mixins import PostRateLimitMixin
from accounts.utils.context import clocks_list_context
from core.models import VirtualClock
from core.services import VirtualClockController
from .models import ThrottleRule
from .exceptions import TokenRefreshTooOften
from .forms import TimeShiftUserCreationForm, UserSettingsForm
from accounts.services.user import UserController

# locale.setlocale(locale.LC_TIME, "uk-UA.UTF-8")

logger = getLogger(__name__)
User = get_user_model()


class SignUpView(PostRateLimitMixin, CreateView):
    form_class = TimeShiftUserCreationForm
    success_url = reverse_lazy("profile_dashboard")
    template_name = "registration/signup.html"
    throttle_scope = ThrottleRule.Scope.GLOBAL

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
        return (VirtualClock.objects.filter(
            Q(user_owner=self.request.user) |
            Q(allowed_users=self.request.user)
        ).select_related('user_owner')
         .prefetch_related('allowed_users')
         .distinct()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        grouped = defaultdict(list)

        clocks = (
            self.get_queryset()
            .select_related("user_owner")
        )

        for clock in clocks:
            if clock.user_owner != self.request.user:
                grouped[clock.user_owner].append(clock)
        shared_count = sum(len(clocks) for clocks in grouped.values())
        context["shared_count"] = shared_count
        context["shared_clocks"] = dict(grouped)
        logger.debug(f"ProfileClocksView.get_context_data(): shared_count: {shared_count}")
        # logger.debug(f"")
        context.update(clocks_list_context(self.request, clocks))
        # logger.debug(
        #     f"accounts.views.ClockDetailView.get_context_data(): clocks={clocks}")
        return context




class ClockDetailView(LoginRequiredMixin, DetailView):
    model = VirtualClock
    template_name = "accounts/clock_detail.html"
    context_object_name = "clock"
    fields = ["current_time", "tick_enabled", "speed"]

    # form_class = VirtualClockForm

    def get_queryset(self):
        # тільки годинники користувача
        return VirtualClock.objects.filter(
            Q(user_owner=self.request.user) |
            Q(allowed_users=self.request.user)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # vcc = VirtualClockController(self.request.user.virtual_clocks.get(id=self.kwargs["pk"]))
        vcc = VirtualClockController(self.object)
        context["current_time"] = vcc.get_time()
        context["allowed_users"] = vcc.virtual_clock.allowed_users.all()
        context["requested_user"] = self.request.user
        context["user_owner"] = vcc.get_user_owner()
        # context['tick_enabled'] = vcc.tick_status
        min_speed, max_speed = VirtualClock._meta.get_field("speed").validators
        context['min_speed'] = min_speed.limit_value
        context['max_speed'] = max_speed.limit_value
        logger.debug(f"accounts.views.ClockDetailView.get_context(): min_speed: {context['min_speed']} "
                     f"max_speed: {context['max_speed']}")
        user_tz = self.request.user.timezone
        dj_tz.activate(user_tz)
        logger.debug(f"Current time: {vcc.get_iso_time()}")
        return context


class ClockCreateView(LoginRequiredMixin, PostRateLimitMixin, CreateView):
    model = VirtualClock
    fields = ["name"]
    template_name = "accounts/clock_create.html"
    success_url = reverse_lazy("profile_clocks")
    throttle_scope = ThrottleRule.Scope.CLOCKS_CREATE

    def form_valid(self, form):
        # додаємо власника
        form.instance.user_owner = self.request.user
        logger.debug(f"Creating clock for user {self.request.user} with name {form.cleaned_data['name']}")
        try:
            return super().form_valid(form)
        except ValidationError as e:
            logger.info(f"ClockCreateView.form_valid(): ValidationError: {e}")
            messages.warning(self.request, "Не вдалося створити годинник. Перевищено ліміт годинників.")
            return redirect("profile_clocks")


class ClockDeleteView(LoginRequiredMixin, PostRateLimitMixin, DeleteView):
    model = VirtualClock
    template_name = "accounts/clock_confirm_delete.html"
    success_url = reverse_lazy("profile_clocks")
    throttle_scope = ThrottleRule.Scope.GLOBAL

    def get_queryset(self):
        # дозволяємо видаляти лише свої годинники
        return self.request.user.virtual_clocks.all()


# ⚙️ 4. Налаштування користувача
class ProfileSettingsView(LoginRequiredMixin, PostRateLimitMixin, UpdateView):
    model = User
    form_class = UserSettingsForm
    template_name = "accounts/settings.html"
    success_url = reverse_lazy("profile_settings")
    throttle_scope = ThrottleRule.Scope.GLOBAL

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Налаштування збережено.")
        return response


class UserTokenUpdateView(LoginRequiredMixin, PostRateLimitMixin, View):
    throttle_scope = ThrottleRule.Scope.TOKEN_REFRESH

    def post(self, request, *args, **kwargs):
        logger.debug(f"UserTokenUpdateView(): post(): old token\n{request.user.api_token}")
        # try:
        user = UserController(self.request.user).update_token()
        logger.debug(f"UserTokenUpdateView(): post(): new token generated:\n{user.api_token}")
        # except TokenRefreshTooOften as e:
        # logger.debug(f"UserTokenUpdateView.post(): token update error")
        # total_seconds = User.get_token_refresh_cooldown().total_seconds()

        # logger.debug(f"UserTokenUpdateView.post(): help(TOKEN_REFRESH_COOLDOWN):{help(User.TOKEN_REFRESH_COOLDOWN)}")

        referer = request.META.get("HTTP_REFERER")
        if referer:
            return redirect(referer)
        else:
            return redirect(reverse('home'))

class ClockControlView(LoginRequiredMixin, PostRateLimitMixin, View):
    throttle_scope = ThrottleRule.Scope.GLOBAL

    def get_queryset(self):
        return VirtualClock.objects.filter(
            Q(user_owner=self.request.user) |
            Q(allowed_users=self.request.user)
        ).distinct()

    def get(self, request, *args, **kwargs):
        # clock_id = kwargs[]
        # logger.debug(f"accounts.views.ClockControlView.get(): kwargs:{kwargs}")
        # logger.debug(f"accounts.views.ClockControlView.get(): clock_id: {clock_id}")
        clock = get_object_or_404(VirtualClock, id=kwargs['pk'])
        controller = VirtualClockController(clock)
        current_time = controller.get_iso_time()
        logger.debug(f"accounts.views.ClockControlView.get(): current_time: {current_time}")
        return JsonResponse({
            "current_time": current_time,
            "timezone": controller.get_time_zone()
        })

    # TODO: separate this method into small pieces
    def post(self, request, *args, **kwargs):
        logger.debug(f"accounts.views.ClockControlView.post()")
        logger.debug(f"accounts.views.ClockControlView.post(): POST params: {request.POST}")
        pk = kwargs.get("pk")
        clock = get_object_or_404(self.get_queryset(), pk=pk)
        controller: VirtualClockController = VirtualClockController(clock)
        if request.headers.get("HX-Request"):
            # Запит прийшов від HTMX
            is_htmx = True
        else:
            # Звичайний POST, не через HTMX
            is_htmx = False

        logger.debug(f"accounts.views.ClockControlView.post(): is_htmx: {is_htmx}")
        context = {"clock": clock,
                   "current_time": controller.get_time(),
                   "allowed_users": clock.allowed_users.all(),
                   }
        # clocks_list_context(self.request, self.get_queryset(), context)
        messages_to_user = []

        # --- Назва ---
        self.__change_name(controller, messages_to_user, request)

        # --- Тікання ---
        element = request.POST.get("toggle_tick")
        logger.debug(f"ClockControlView.post(): element: {element}")
        if not is_htmx:
            self.__toggle_tick(controller, element, messages_to_user)
        else:
            logger.debug(f"ClockControlView.post(): toggle_tick == {request.POST.get('toggle_tick')}")
            if request.POST.get('toggle_tick') == "button":
                context = self.__htmx_toggle_tick(clock, context, controller, messages_to_user)
                return render(
                    request,
                    "includes/clock_item.html",
                    context
                )

        # --- Час ---
        current_time = request.POST.get("current_time")
        if current_time:
            try:
                self.__update_time(controller, current_time, messages_to_user, request)
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
        # --- Встановити швидкість часу
        old_speed = controller.get_clock_speed()
        new_speed = request.POST.get("clock_speed")
        self.__set_time_speed(controller, new_speed, old_speed, request)

        # --- Додати користувачів ---
        if self.request.user == clock.user_owner:
            add_user_id = request.POST.get("add_user_id")
            if add_user_id:
                self.__add_users(add_user_id, clock, controller, messages_to_user, request)
                return render(
                    request,
                    "includes/allowed_users_table.html",
                    context,
                )

            # --- Видалити користувачів ---
            remove_user_id = request.POST.get("remove_user_id")
            if remove_user_id:
                self.__remove_users(add_user_id, controller, messages_to_user, remove_user_id, request)
                return render(
                    request,
                    "includes/allowed_users_table.html",
                    context
                )

            # --- Відправка повідомлень ---
        self.__send_messages(controller, messages_to_user, pk, request)

        next_url = self.__check_for_next_url(request)

        return redirect(next_url)

    @staticmethod
    def __check_for_next_url(request) -> Any:
        next_url = request.POST.get("next")

        if not next_url or not url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
        ):
            next_url = reverse("home")
        return next_url

    @staticmethod
    def __send_messages(controller: VirtualClockController, messages_to_user: list[Any], pk: Any | None, request):
        for msg in messages_to_user:
            messages.success(request, msg)
            logger.info(f"accounts.views.ClockControlView: Clock(pk={pk}): {msg}")
        controller.save()

    def __remove_users(self, add_user_id, controller: VirtualClockController, messages_to_user: list[Any],
                       remove_user_id, request):
        remove_user = User.objects.filter(id=remove_user_id).first()
        if remove_user:
            username = remove_user.username
            logger.debug(f"ClockControlView.post(): remove user:"
                         f" username {username} ID {remove_user_id}")
            controller.update_allowed_users({'remove_users': [remove_user_id]})
            m = f"Користувача {username} з ID {remove_user_id} видалено"
            messages_to_user.append(m)
            messages.error(request, m)
        else:
            m = "Користувача з таким ID не існує"
            messages_to_user.append(m)
            messages.error(request, m)
            logger.debug(
                f"ClockControlView.post(): add_user ID: {add_user_id}: користувача з таким ID не існує")

    @staticmethod
    def __add_users(add_user_id, clock: VirtualClock, controller: VirtualClockController,
                    messages_to_user: list[Any], request):
        user = User.objects.filter(id=add_user_id).first()
        if not user:
            m = "Користувача з таким ID не існує"
            messages_to_user.append(m)
            messages.error(request, m)
            logger.debug(
                f"ClockControlView.post(): add_user ID: {add_user_id}: користувача з таким ID не існує")
            # return HttpResponse(
            #     f"<div class='alert alert-info alert-dismissible fade show'>Юзер {user.id} не існує</div>"
            # )
        elif clock.allowed_users.filter(id=user.id).exists():
            m = "Користувач уже має доступ"
            logger.debug(
                f"ClockControlView.post(): add_user ID: {add_user_id}: користувач з таким ID вже має доступ")
            messages_to_user.append(m)
            messages.info(request, m)
            # return HttpResponse(
            #     f"<div class='alert alert-info alert-dismissible fade show'>Юзер {user.id} вже має доступ</div>"
            # )
        else:
            m = f"Доступ надано: {user.username}"
            logger.debug(f"ClockControlView.post(): add_user ID: {add_user_id}: "
                         f"надано доступ користувачу {user.username}")
            messages_to_user.append(m)
            controller.update_allowed_users({'add_users': [add_user_id]})
            messages.success(request, m)

    def __set_time_speed(self, controller: VirtualClockController, new_speed, old_speed: float, request):
        logger.debug(f"accounts.views.ClockControlView.post(): old_speed: {old_speed} new_speed: {new_speed}")
        if new_speed and old_speed != float(new_speed):
            try:
                controller.set_clock_speed(new_speed, save=False)
                logger.debug(f"accounts.views.ClockControlView.post(): set speed multiplier to: {new_speed}")
                messages.info(request, f"Змінений коефіцієнт швидкості на {new_speed}")
            except ValidationError as e:
                logger.debug(f"accounts.views.ClockControlView.post(): exception: speed out of limit:{new_speed}")
                messages.error(request,
                               e.message_dict['speed'][0] if hasattr(e, "message_dict") else e.messages)

    def __update_time(self, controller: VirtualClockController, current_time, messages_to_user: list[Any], request):
        tz = pytz.timezone(request.user.timezone)
        dt_naive = datetime.datetime.fromisoformat(current_time)
        dt_user = tz.localize(dt_naive)
        controller.set_time(dt_user, save=False, tick_auto_pause=False)
        messages_to_user.append(
            f"Час годинника оновлено на {dt_user}"
        )

    @staticmethod
    def __toggle_tick(controller: VirtualClockController, element, messages_to_user: list[Any]):
        logger.debug(f"ClockControlView.post(): if tick_enabled != controller.tick_status not htmx")
        if element == "checkbox" and not controller.tick_status:
            # if tick_enabled != controller.tick_status:
            controller.toggle_tick(enabled=True, save=False)  # або окремий метод set_tick(tick_enabled)
            state = "увімкнено"  # if tick_enabled else "вимкнено"
            messages_to_user.append(f"Тікання годинника {state}")
        elif not element and controller.tick_status:
            controller.toggle_tick(enabled=False, save=False)
            state = "вимкнено"
            messages_to_user.append(f"Тікання годинника {state}")

    @staticmethod
    def __htmx_toggle_tick(clock: VirtualClock, context: dict[str, VirtualClock],
                         controller: VirtualClockController, messages_to_user: list[Any]) -> dict[str, VirtualClock]:
        logger.debug(f"ClockControlView.post(): request.POST.get('toggle_tick'): htmx_toggle_tick():")
        controller.toggle_tick()
        state = "увімкнено" if controller.tick_status else "вимкнено"
        messages_to_user.append(f"Тікання годинника {state}")
        context = {"clock": clock}
        context.update(clocks_list_context(ClockControlView.request, ClockControlView.get_queryset()))
        return context

    @staticmethod
    def __change_name(controller: VirtualClockController, messages_to_user: list[Any], request):
        name = request.POST.get("clock_name")
        if name and name != controller.clock_name:
            controller.set_clock_name(name, save=False)
            messages_to_user.append(f"Назва годинника змінена на {name}")


class UserSearchView(LoginRequiredMixin, View):
    USERNAME_RE = r'^[\w.@+-]+$'

    @staticmethod
    def is_valid_username(value: str) -> bool:
        return bool(re.fullmatch(UserSearchView.USERNAME_RE, value))

    def get(self, request, clock_id):
        logger.debug(f"accounts.views.UserSearchByIdView.get(): start")
        raw_user_input = request.GET.get("user_id", "").strip()
        logger.debug(f"accounts.views.UserSearchByIdView.get(): clock_id:{clock_id} raw_user_id:{raw_user_input}")

        if str(raw_user_input) == "":
            logger.debug(f"accounts.views.UserSearchByIdView.get(): empty input")
            return HttpResponse()
        elif raw_user_input.isdigit():
            user_id = int(raw_user_input)
            logger.debug(f"accounts.views.UserSearchByIdView.get(): looking for user id:{user_id}")
            user = (
                User.objects
                .filter(id=user_id)
                .exclude(virtual_clocks__id=clock_id).exclude(shared_clocks__id=clock_id)
                .first()
            )
            logger.debug(f"accounts.views.UserSearchByIdView.get(): user: {user}")
            return render(
                request,
                "includes/user_search_by_id.html",
                {'found_user': user, 'clock_id': clock_id}
            )
        elif self.is_valid_username(raw_user_input):
            username = raw_user_input
            logger.debug(f"accounts.views.UserSearchByIdView.get(): looking for user id:{username}")
            user = (
                User.objects
                .filter(username=username)
                .exclude(virtual_clocks__id=clock_id).exclude(shared_clocks__id=clock_id)
                .first()
            )
            logger.debug(
                f"accounts.views.UserSearchByIdView.get(): looking for user id:{"Found" if user else "Not Found"}")
            return render(
                request,
                "includes/user_search_by_id.html",
                {'found_user': user, 'clock_id': clock_id}
            )
        else:
            logger.debug(f"accounts.views.UserSearchByIdView.get(): not valid input")
            return render(
                request,
                "includes/user_search_by_id.html",
                {'found_user': ""}
            )
