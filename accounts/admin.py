from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Household


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "household",
        "is_staff",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "household")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "phone_number", "date_of_birth")},
        ),
        (_("Preferences"), {"fields": ("dietary_restrictions",)}),
        (_("Household"), {"fields": ("household", "is_household_admin")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "fields": ("last_login", "date_joined", "created_at", "updated_at"),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at", "date_joined", "last_login")


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    """Admin configuration for Household model."""

    list_display = ("name", "invite_code", "created_by", "member_count", "created_at")
    list_filter = ("created_at", "currency", "timezone")
    search_fields = ("name", "invite_code")
    readonly_fields = ("invite_code", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "invite_code")}),
        (_("Settings"), {"fields": ("timezone", "currency")}),
        (_("Metadata"), {"fields": ("created_by", "created_at", "updated_at")}),
    )

    def member_count(self, obj):
        """Display the number of members in the household."""
        return obj.members.count()

    member_count.short_description = _("Members")
