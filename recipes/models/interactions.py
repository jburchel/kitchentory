"""
Recipe interaction models: user interactions, reviews, and cooking sessions.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

from .recipe import Recipe
from .steps import RecipeStep

User = get_user_model()


class UserRecipeInteraction(models.Model):
    """
    Track user interactions with recipes (views, likes, ratings, cooking history).
    """

    INTERACTION_TYPES = (
        ("view", _("Viewed")),
        ("like", _("Liked")),
        ("save", _("Saved")),
        ("cook", _("Cooked")),
        ("rate", _("Rated")),
        ("share", _("Shared")),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recipe_interactions"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="user_interactions"
    )
    interaction_type = models.CharField(
        _("interaction type"), max_length=10, choices=INTERACTION_TYPES
    )

    # User preferences and ratings
    rating = models.IntegerField(
        _("rating"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    is_favorite = models.BooleanField(_("favorite"), default=False)
    times_cooked = models.IntegerField(_("times cooked"), default=0)

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_recipe_interactions"
        verbose_name = _("user recipe interaction")
        verbose_name_plural = _("user recipe interactions")
        unique_together = ["user", "recipe", "interaction_type"]
        indexes = [
            models.Index(fields=["user", "interaction_type"]),
            models.Index(fields=["recipe", "interaction_type"]),
        ]

    def __str__(self):
        return f"{self.user.username} {self.get_interaction_type_display()} {self.recipe.title}"

    def increment_cooked_count(self):
        """Increment the times cooked counter."""
        self.times_cooked += 1
        self.save()


class RecipeReview(models.Model):
    """
    User reviews and ratings for recipes.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recipe_reviews"
    )
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="reviews")

    # Review Content
    rating = models.IntegerField(
        _("rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Rating from 1 to 5 stars"),
    )
    title = models.CharField(_("review title"), max_length=200, blank=True)
    comment = models.TextField(
        _("comment"), blank=True, help_text=_("Optional detailed review")
    )

    # Recipe Modifications
    made_modifications = models.BooleanField(_("made modifications"), default=False)
    modifications_description = models.TextField(
        _("modifications description"),
        blank=True,
        help_text=_("Describe any changes made to the original recipe"),
    )

    # Cooking Context
    difficulty_rating = models.IntegerField(
        _("difficulty rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_(
            "How difficult was this recipe to make? (1=very easy, 5=very hard)"
        ),
    )
    would_make_again = models.BooleanField(_("would make again"), null=True, blank=True)
    cooking_time_actual = models.IntegerField(
        _("actual cooking time (minutes)"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("How long did it actually take you?"),
    )

    # Metadata
    is_verified_cook = models.BooleanField(
        _("verified cook"),
        default=False,
        help_text=_("User has demonstrated they actually cooked this recipe"),
    )
    helpful_votes = models.IntegerField(_("helpful votes"), default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recipe_reviews"
        verbose_name = _("recipe review")
        verbose_name_plural = _("recipe reviews")
        unique_together = ["user", "recipe"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review by {self.user.username} for {self.recipe.name or self.recipe.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update recipe rating after saving review
        self.recipe.update_rating()


class CookingSession(models.Model):
    """
    Track individual cooking sessions for recipes.
    """

    SESSION_STATUSES = (
        ("planning", _("Planning")),
        ("shopping", _("Shopping")),
        ("prepping", _("Prepping")),
        ("cooking", _("Cooking")),
        ("completed", _("Completed")),
        ("paused", _("Paused")),
        ("abandoned", _("Abandoned")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="cooking_sessions"
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="cooking_sessions"
    )

    # Session Details
    status = models.CharField(
        _("status"), max_length=15, choices=SESSION_STATUSES, default="planning"
    )
    servings_planned = models.IntegerField(
        _("planned servings"), validators=[MinValueValidator(1)], default=4
    )
    current_step = models.ForeignKey(
        RecipeStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_sessions",
    )

    # Timing
    started_at = models.DateTimeField(_("started at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    total_cooking_time = models.IntegerField(
        _("total cooking time (minutes)"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    # Notes and Modifications
    notes = models.TextField(
        _("session notes"), blank=True, help_text=_("Notes about this cooking session")
    )
    modifications_made = models.TextField(
        _("modifications made"), blank=True, help_text=_("Changes made during cooking")
    )

    # Results
    success_rating = models.IntegerField(
        _("success rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("How well did the recipe turn out? (1=disaster, 5=perfect)"),
    )
    would_repeat = models.BooleanField(_("would repeat"), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cooking_sessions"
        verbose_name = _("cooking session")
        verbose_name_plural = _("cooking sessions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} cooking {self.recipe.title} ({self.get_status_display()})"

    @property
    def is_active(self):
        """Check if this is an active cooking session."""
        return self.status in ["planning", "shopping", "prepping", "cooking", "paused"]

    @property
    def progress_percentage(self):
        """Calculate cooking progress as percentage."""
        if not self.current_step:
            return 0

        total_steps = self.recipe.total_steps_count
        if total_steps == 0:
            return 0

        return (self.current_step.step_number / total_steps) * 100

    def start_cooking(self):
        """Mark session as started."""
        if not self.started_at:
            self.started_at = timezone.now()
        self.status = "cooking"
        self.save()

    def complete_cooking(self):
        """Mark session as completed."""
        self.completed_at = timezone.now()
        self.status = "completed"
        if self.started_at:
            self.total_cooking_time = int(
                (self.completed_at - self.started_at).total_seconds() / 60
            )
        self.save()

        # Create cooking interaction
        UserRecipeInteraction.objects.get_or_create(
            user=self.user, recipe=self.recipe, interaction_type="cook"
        )