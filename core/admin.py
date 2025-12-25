from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import VirtualClock

User = get_user_model()

# Форма для адмінки, щоб контролювати allowed_users
class VirtualClockAdminForm(forms.ModelForm):
    class Meta:
        model = VirtualClock
        fields = "__all__"

    def clean_allowed_users(self):
        allowed = self.cleaned_data.get("allowed_users")
        owner = self.cleaned_data.get("user_owner")
        if owner and allowed and owner in allowed:
            raise forms.ValidationError("Owner cannot be in allowed_users.")
        return allowed

@admin.register(VirtualClock)
class VirtualClockAdmin(admin.ModelAdmin):
    form = VirtualClockAdminForm
    filter_horizontal = ("allowed_users",)
    list_display = ("user_owner", "id")

    # Щоб не показувати власника у списку для allowed_users
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "allowed_users":
            obj_id = request.resolver_match.kwargs.get("object_id")
            obj = self.get_object(request, obj_id)
            if obj:
                kwargs["queryset"] = User.objects.exclude(id=obj.user_owner_id)
            else:
                kwargs["queryset"] = User.objects.all()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

