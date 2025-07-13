from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework import permissions


class IsHouseholdMember(permissions.BasePermission):
    """
    Custom permission to only allow members of the same household
    to view and modify household data.
    """

    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user.is_authenticated:
            return False

        # User must have a household
        if not hasattr(request.user, "household") or not request.user.household:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        # Check if the object has a household attribute
        if hasattr(obj, "household"):
            return obj.household == request.user.household

        # Check if the object has a user attribute that has a household
        if hasattr(obj, "user"):
            return obj.user.household == request.user.household

        # Check if the object has a created_by attribute
        if hasattr(obj, "created_by"):
            return obj.created_by.household == request.user.household

        # Default to False for safety
        return False


def household_required(view_func):
    """
    Decorator for views that checks that the user is logged in and has a household.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this page.")

        if not hasattr(request.user, "household") or not request.user.household:
            raise PermissionDenied(
                "You must be part of a household to access this page."
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def verify_household_ownership(user, obj):
    """
    Verify that a user has access to an object based on household membership.
    Raises PermissionDenied if the user doesn't have access.
    """
    if not user.is_authenticated:
        raise PermissionDenied("You must be logged in.")

    if not hasattr(user, "household") or not user.household:
        raise PermissionDenied("You must be part of a household.")

    # Check various possible household relationships
    obj_household = None

    if hasattr(obj, "household"):
        obj_household = obj.household
    elif hasattr(obj, "user") and hasattr(obj.user, "household"):
        obj_household = obj.user.household
    elif hasattr(obj, "created_by") and hasattr(obj.created_by, "household"):
        obj_household = obj.created_by.household

    if obj_household != user.household:
        raise PermissionDenied("You don't have permission to access this item.")

    return True


class HouseholdQuerySetMixin:
    """
    Mixin for ViewSets to automatically filter querysets by household.
    """

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_authenticated:
            return queryset.none()

        if (
            not hasattr(self.request.user, "household")
            or not self.request.user.household
        ):
            return queryset.none()

        # Filter by household
        if hasattr(queryset.model, "household"):
            return queryset.filter(household=self.request.user.household)
        elif hasattr(queryset.model, "user"):
            return queryset.filter(user__household=self.request.user.household)
        elif hasattr(queryset.model, "created_by"):
            return queryset.filter(created_by__household=self.request.user.household)

        return queryset
