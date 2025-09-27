from django.contrib import admin
from  .models import TimeShiftUser

@admin.register(TimeShiftUser)
class TimeShiftUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active', 'is_superuser')
    # list_filter = ('is_staff', 'is_active', 'is_superuser')
    # search_fields = ('username', 'email')
    # ordering = ('username',)

