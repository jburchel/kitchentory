from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Profile URLs
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),
    # Household URLs
    path("household/", views.household_view, name="household"),
    path("household/create/", views.household_create_view, name="household_create"),
    path("household/join/", views.household_join_view, name="household_join"),
    path("household/leave/", views.household_leave_view, name="household_leave"),
    path(
        "household/settings/", views.household_settings_view, name="household_settings"
    ),
]
