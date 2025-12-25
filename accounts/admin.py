from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import TimeShiftUser


@admin.register(TimeShiftUser)
class TimeShiftUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ("TimeShift", {"fields": ("timezone",)}),
    )
    # list_filter = ('is_staff', 'is_active', 'is_superuser')
    # search_fields = ('username', 'email')
    # ordering = ('username',)

