from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import TimeShiftUser, Plan, ThrottleRule, UserSubscription


@admin.register(TimeShiftUser)
class TimeShiftUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'is_staff', 'is_active', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ("TimeShift", {"fields": ("timezone", 'max_clocks_count')}),
    )
    # list_filter = ('is_staff', 'is_active', 'is_superuser')
    # search_fields = ('username', 'email')
    # ordering = ('username',)

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'is_active')

@admin.register(ThrottleRule)
class ThrottleRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'plan', 'scope', 'max_requests', 'period')

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan', 'started_at', 'expires_at')