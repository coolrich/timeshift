from django.urls import path

from .views import SignUpView, ProfileDashboardView, ProfileSettingsView, ProfileClocksView, \
    ProfileTokensView, ClockDetailView, ClockCreateView, ClockDeleteView, ClockStateControlView, ClockTimeControlView, \
    UserTokenUpdateView, ClockControlView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('signup/', SignUpView.as_view(), name='signup'),

    path('', ProfileDashboardView.as_view(), name='profile_dashboard'),
    path('tokens/', ProfileTokensView.as_view(), name='profile_tokens'),
    path('clocks/', ProfileClocksView.as_view(), name='profile_clocks'),
    # path("clocks/<int:pk>/edit-time/", ClockTimeControlView.as_view(), name="clock_edit_time"),
    path("clocks/<int:pk>/control/", ClockControlView.as_view(), name="clock_control"),
    path("clocks/<int:pk>/", ClockDetailView.as_view(), name="clock_detail"),
    path("clocks/new/", ClockCreateView.as_view(), name="clock_create"),
    path("clocks/<int:pk>/delete/", ClockDeleteView.as_view(), name="clock_delete"),
    path('settings/', ProfileSettingsView.as_view(), name='profile_settings'),
    path('user/', UserTokenUpdateView.as_view(), name='user_token_update')
    # path("api/", "accounts.api.router", name="accounts_api"),
]
