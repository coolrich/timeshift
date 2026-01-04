from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import TimeShiftUser


@admin.register(TimeShiftUser)
class TimeShiftUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'is_staff', 'is_active', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ("TimeShift", {"fields": ("timezone", 'max_clocks_count')}),
    )
    # list_filter = ('is_staff', 'is_active', 'is_superuser')
    # search_fields = ('username', 'email')
    # ordering = ('username',)

