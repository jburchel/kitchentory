from django.db import models


class HouseholdScopedManager(models.Manager):
    """
    Manager that automatically filters queries by the user's household.
    This provides an additional layer of security for household-scoped data.
    """

    def for_household(self, household):
        """Filter queryset by household."""
        if hasattr(self.model, "household"):
            return self.filter(household=household)
        elif hasattr(self.model, "user"):
            return self.filter(user__household=household)
        elif hasattr(self.model, "created_by"):
            return self.filter(created_by__household=household)
        else:
            # If no household relationship found, return empty queryset for safety
            return self.none()

    def for_user_household(self, user):
        """Filter queryset by the user's household."""
        if not user.is_authenticated:
            return self.none()

        if not hasattr(user, "household") or not user.household:
            return self.none()

        return self.for_household(user.household)


class HouseholdScopedQuerySet(models.QuerySet):
    """
    QuerySet that provides household-scoped filtering methods.
    """

    def for_household(self, household):
        """Filter by household."""
        if hasattr(self.model, "household"):
            return self.filter(household=household)
        elif hasattr(self.model, "user"):
            return self.filter(user__household=household)
        elif hasattr(self.model, "created_by"):
            return self.filter(created_by__household=household)
        else:
            return self.none()

    def for_user_household(self, user):
        """Filter by the user's household."""
        if not user.is_authenticated:
            return self.none()

        if not hasattr(user, "household") or not user.household:
            return self.none()

        return self.for_household(user.household)
