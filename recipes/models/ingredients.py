"""
Recipe ingredient models.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from fractions import Fraction

from .recipe import Recipe


class RecipeIngredient(models.Model):
    """
    Ingredients for a recipe with quantities and preparation notes.
    """

    QUANTITY_UNITS = (
        ("count", _("Count")),
        ("g", _("Grams")),
        ("kg", _("Kilograms")),
        ("ml", _("Milliliters")),
        ("l", _("Liters")),
        ("oz", _("Ounces")),
        ("lb", _("Pounds")),
        ("cup", _("Cups")),
        ("tbsp", _("Tablespoons")),
        ("tsp", _("Teaspoons")),
        ("pinch", _("Pinch")),
        ("dash", _("Dash")),
        ("slice", _("Slice")),
        ("clove", _("Clove")),
        ("bunch", _("Bunch")),
        ("head", _("Head")),
        ("can", _("Can")),
        ("jar", _("Jar")),
        ("package", _("Package")),
        ("to_taste", _("To taste")),
    )

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="ingredients"
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        null=True,
        blank=True,
        help_text=_("Link to product in inventory system"),
    )

    # Ingredient Details
    name = models.CharField(
        _("ingredient name"),
        max_length=200,
        help_text=_(
            'Name as it appears in recipe (e.g., "large onion", "fresh basil")'
        ),
    )
    quantity = models.DecimalField(
        _("quantity"),
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    unit = models.CharField(
        _("unit"), max_length=20, choices=QUANTITY_UNITS, blank=True
    )
    preparation = models.CharField(
        _("preparation"),
        max_length=200,
        blank=True,
        help_text=_('e.g., "diced", "chopped", "minced", "at room temperature"'),
    )

    # Organization
    group = models.CharField(
        _("ingredient group"),
        max_length=100,
        blank=True,
        help_text=_('e.g., "For the sauce", "For the topping", "Garnish"'),
    )
    order = models.IntegerField(_("display order"), default=0)

    # Flags
    is_optional = models.BooleanField(_("optional ingredient"), default=False)
    is_garnish = models.BooleanField(_("garnish"), default=False)

    # Notes
    notes = models.TextField(
        _("notes"),
        blank=True,
        help_text=_("Additional preparation or substitution notes"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recipe_ingredients"
        verbose_name = _("recipe ingredient")
        verbose_name_plural = _("recipe ingredients")
        ordering = ["order", "id"]
        unique_together = ["recipe", "order"]

    def __str__(self):
        parts = []
        if self.quantity:
            parts.append(str(self.quantity))
        if self.unit:
            parts.append(self.unit)  # Use unit value instead of display
        # Use product name if available, otherwise use name
        display_name = self.product.name if self.product else self.name
        parts.append(display_name)
        if self.preparation:
            parts.append(f"({self.preparation})")
        return " ".join(parts)

    @property
    def display_quantity(self):
        """Human-readable quantity display."""
        if not self.quantity:
            return ""

        # Convert decimal to fraction for common cooking amounts
        try:
            frac = Fraction(self.quantity).limit_denominator(16)
            if frac.denominator == 1:
                return str(frac.numerator)
            else:
                return str(frac)
        except:
            return str(self.quantity)

    @property
    def full_description(self):
        """Full ingredient description for display."""
        parts = []

        # Quantity and unit
        if self.quantity and self.unit:
            parts.append(f"{self.display_quantity} {self.get_unit_display()}")
        elif self.quantity:
            parts.append(self.display_quantity)
        elif self.unit == "to_taste":
            parts.append(self.get_unit_display())

        # Name with preparation
        if self.preparation:
            parts.append(f"{self.name}, {self.preparation}")
        else:
            parts.append(self.name)

        # Optional indicator
        if self.is_optional:
            parts.append("(optional)")

        return " ".join(parts)