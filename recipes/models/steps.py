"""
Recipe step models.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

from .recipe import Recipe
from .ingredients import RecipeIngredient


class RecipeStep(models.Model):
    """
    Individual steps for a recipe with timing and equipment info.
    """

    STEP_TYPES = (
        ("prep", _("Preparation")),
        ("cook", _("Cooking")),
        ("bake", _("Baking")),
        ("fry", _("Frying")),
        ("boil", _("Boiling")),
        ("mix", _("Mixing")),
        ("rest", _("Resting/Waiting")),
        ("serve", _("Serving")),
        ("other", _("Other")),
    )

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="steps")

    # Step Content
    step_number = models.IntegerField(
        _("step number"), validators=[MinValueValidator(1)]
    )
    title = models.CharField(
        _("step title"),
        max_length=200,
        blank=True,
        help_text=_('Optional title for the step (e.g., "Prepare the sauce")'),
    )
    instruction = models.TextField(
        _("instruction"), help_text=_("Detailed step-by-step instruction")
    )
    step_type = models.CharField(
        _("step type"), max_length=10, choices=STEP_TYPES, default="other"
    )

    # Timing
    time_minutes = models.IntegerField(
        _("time (minutes)"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Time required for this step"),
    )
    temperature = models.IntegerField(
        _("temperature"),
        null=True,
        blank=True,
        help_text=_("Cooking temperature in Celsius"),
    )
    temperature_unit = models.CharField(
        _("temperature unit"),
        max_length=1,
        choices=(("C", "Celsius"), ("F", "Fahrenheit")),
        default="C",
    )

    # Equipment and Ingredients
    equipment_needed = models.CharField(
        _("equipment needed"),
        max_length=200,
        blank=True,
        help_text=_('e.g., "large skillet", "food processor", "oven"'),
    )
    ingredients_used = models.ManyToManyField(
        RecipeIngredient,
        blank=True,
        related_name="used_in_steps",
        help_text=_("Ingredients used in this step"),
    )

    # Media
    image = models.ImageField(
        _("step image"),
        upload_to="recipes/steps/",
        null=True,
        blank=True,
        help_text=_("Optional image showing the result of this step"),
    )
    video_url = models.URLField(
        _("step video URL"),
        blank=True,
        help_text=_("Optional video demonstration of this step"),
    )

    # Additional Info
    tips = models.TextField(
        _("tips and notes"),
        blank=True,
        help_text=_("Additional tips or troubleshooting notes for this step"),
    )
    is_critical = models.BooleanField(
        _("critical step"),
        default=False,
        help_text=_("Mark as critical if this step significantly affects the outcome"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recipe_steps"
        verbose_name = _("recipe step")
        verbose_name_plural = _("recipe steps")
        ordering = ["step_number"]
        unique_together = ["recipe", "step_number"]

    def __str__(self):
        if self.title:
            return f"Step {self.step_number}: {self.title}"
        instruction_text = self.instruction[:50]
        if len(self.instruction) > 50:
            instruction_text += "..."
        return f"Step {self.step_number}: {instruction_text}"

    @property
    def temperature_display(self):
        """Display temperature with unit."""
        if not self.temperature:
            return ""
        return f"{self.temperature}°{self.temperature_unit}"

    @property
    def time_display(self):
        """Human-readable time display."""
        if not self.time_minutes:
            return ""

        if self.time_minutes < 60:
            return f"{self.time_minutes} minutes"
        else:
            hours = self.time_minutes // 60
            minutes = self.time_minutes % 60
            if minutes == 0:
                return f"{hours} hour{'s' if hours > 1 else ''}"
            else:
                return f"{hours}h {minutes}m"

    @property
    def ingredient_list(self):
        """Get ingredients used in this step."""
        return self.ingredients_used.all()

    def get_next_step(self):
        """Get the next step in the recipe."""
        return self.recipe.steps.filter(step_number__gt=self.step_number).first()

    def get_previous_step(self):
        """Get the previous step in the recipe."""
        return self.recipe.steps.filter(step_number__lt=self.step_number).last()