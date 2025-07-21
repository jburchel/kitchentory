from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Email is used as the primary authentication field.
    """

    email = models.EmailField(_("email address"), unique=True)

    # Additional profile fields
    phone_number = models.CharField(_("phone number"), max_length=20, blank=True)
    date_of_birth = models.DateField(_("date of birth"), null=True, blank=True)

    # Preferences
    dietary_restrictions = models.JSONField(
        _("dietary restrictions"),
        default=list,
        help_text=_("List of dietary restrictions (e.g., vegetarian, gluten-free)"),
    )

    # Household management
    household = models.ForeignKey(
        "Household",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    is_household_admin = models.BooleanField(
        _("household admin"),
        default=True,
        help_text=_("Designates whether the user can manage household settings."),
    )

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Subscription fields
    current_plan = models.ForeignKey(
        'subscriptions.SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Current subscription plan (cached for quick access)"
    )
    subscription_status = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text="Current subscription status (cached for quick access)"
    )
    trial_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End date of trial period"
    )
    subscription_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End date of current subscription period"
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Stripe customer ID for payment processing"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.email
    
    def get_subscription_plan(self):
        """Get user's subscription plan, defaulting to free if none."""
        if hasattr(self, 'subscription') and self.subscription.is_active:
            return self.subscription.plan
        # Return cached plan or free plan
        if self.current_plan:
            return self.current_plan
        # Import here to avoid circular imports
        from subscriptions.models import SubscriptionPlan
        try:
            return SubscriptionPlan.objects.get(tier='free')
        except SubscriptionPlan.DoesNotExist:
            return None
    
    def has_premium_features(self):
        """Check if user has at least premium tier."""
        plan = self.get_subscription_plan()
        return plan and plan.tier in ['premium', 'pro']
    
    def has_pro_features(self):
        """Check if user has pro tier."""
        plan = self.get_subscription_plan()
        return plan and plan.tier == 'pro'
    
    def can_use_feature(self, feature_name):
        """Check if user can use a specific feature based on their plan."""
        plan = self.get_subscription_plan()
        if not plan:
            return False
        return getattr(plan, f'has_{feature_name}', False)


class Household(models.Model):
    """
    Represents a household that can have multiple users.
    Enables sharing of inventory, recipes, and shopping lists.
    """

    name = models.CharField(_("household name"), max_length=100)
    invite_code = models.CharField(
        _("invite code"),
        max_length=20,
        unique=True,
        help_text=_("Code for inviting new members"),
    )

    # Settings
    timezone = models.CharField(
        _("timezone"),
        max_length=50,
        default="UTC",
        help_text=_("Timezone for scheduling and notifications"),
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="USD",
        help_text=_("Currency code for shopping lists"),
    )

    # Tracking
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="households_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "households"
        verbose_name = _("household")
        verbose_name_plural = _("households")

    def __str__(self):
        return self.name

    def generate_invite_code(self):
        """Generate a unique invite code for the household."""
        import string
        import random

        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Household.objects.filter(invite_code=code).exists():
                self.invite_code = code
                break
        return self.invite_code

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.generate_invite_code()
        super().save(*args, **kwargs)
