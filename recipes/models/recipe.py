"""
Core Recipe model.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
import uuid

from .base import RecipeCategory, RecipeTag

User = get_user_model()


class Recipe(models.Model):
    """
    Recipe with comprehensive metadata for matching and cooking.
    """

    DIFFICULTY_CHOICES = (
        ("easy", _("Easy")),
        ("medium", _("Medium")),
        ("hard", _("Hard")),
    )

    SERVING_UNITS = (
        ("servings", _("Servings")),
        ("portions", _("Portions")),
        ("people", _("People")),
        ("pieces", _("Pieces")),
    )

    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        _("name"), max_length=200, db_index=True, default="Untitled Recipe"
    )
    title = models.CharField(
        _("title"), max_length=200, db_index=True, default="Untitled Recipe"
    )
    slug = models.SlugField(_("slug"), unique=True, max_length=220, blank=True)
    description = models.TextField(_("description"), blank=True)
    instructions = models.TextField(_("instructions"), blank=True)

    # Author
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_recipes",
        verbose_name=_("created by"),
    )

    # Classification
    category = models.ForeignKey(
        RecipeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recipes",
    )
    tags = models.ManyToManyField(RecipeTag, blank=True, related_name="recipes")

    # Timing and Difficulty
    prep_time = models.IntegerField(
        _("preparation time (minutes)"),
        validators=[MinValueValidator(0)],
        help_text=_("Time to prepare ingredients"),
        default=0,
    )
    cook_time = models.IntegerField(
        _("cooking time (minutes)"),
        validators=[MinValueValidator(0)],
        help_text=_("Time to cook the recipe"),
        default=0,
    )
    total_time = models.IntegerField(
        _("total time (minutes)"),
        validators=[MinValueValidator(0)],
        help_text=_("Total time including prep and cook"),
        default=0,
    )
    difficulty = models.CharField(
        _("difficulty"), max_length=10, choices=DIFFICULTY_CHOICES, default="easy"
    )

    # Serving Information
    servings = models.IntegerField(
        _("servings"), validators=[MinValueValidator(1)], default=4
    )
    serving_unit = models.CharField(
        _("serving unit"), max_length=20, choices=SERVING_UNITS, default="servings"
    )

    # Nutritional Information (optional)
    calories_per_serving = models.IntegerField(
        _("calories per serving"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    protein_grams = models.DecimalField(
        _("protein (grams)"),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    carb_grams = models.DecimalField(
        _("carbohydrates (grams)"),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    fat_grams = models.DecimalField(
        _("fat (grams)"),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    # Media
    image = models.ImageField(
        _("recipe image"), upload_to="recipes/", null=True, blank=True
    )
    image_url = models.URLField(_("external image URL"), blank=True, null=True)
    video_url = models.URLField(
        _("video URL"), blank=True, help_text=_("YouTube, Vimeo, etc.")
    )

    # Source Information
    source_name = models.CharField(
        _("source name"),
        max_length=200,
        blank=True,
        help_text=_('e.g., "Grandma\'s Recipe", "Food Network", etc.'),
    )
    source_url = models.URLField(
        _("source URL"), blank=True, help_text=_("Original recipe URL if imported")
    )
    author = models.CharField(_("author"), max_length=200, blank=True)

    # User and Status
    is_public = models.BooleanField(_("public recipe"), default=False)
    is_verified = models.BooleanField(_("verified recipe"), default=False)

    # Dietary Restrictions
    is_vegetarian = models.BooleanField(_("vegetarian"), default=False)
    is_vegan = models.BooleanField(_("vegan"), default=False)
    is_gluten_free = models.BooleanField(_("gluten-free"), default=False)
    is_dairy_free = models.BooleanField(_("dairy-free"), default=False)
    is_nut_free = models.BooleanField(_("nut-free"), default=False)

    # Metadata
    view_count = models.IntegerField(_("view count"), default=0)
    like_count = models.IntegerField(_("like count"), default=0)
    rating_average = models.DecimalField(
        _("average rating"),
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    rating_count = models.IntegerField(_("rating count"), default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recipes"
        verbose_name = _("recipe")
        verbose_name_plural = _("recipes")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["category", "difficulty"]),
            models.Index(fields=["total_time", "servings"]),
            models.Index(fields=["is_public", "is_verified"]),
        ]

    def __str__(self):
        return self.name or self.title

    def save(self, *args, **kwargs):
        # Generate slug if not set
        if not self.slug:
            from django.utils.text import slugify

            base_slug = slugify(self.name or self.title)
            slug = base_slug
            counter = 1
            while Recipe.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Auto-calculate total time if not provided
        if not self.total_time and (self.prep_time or self.cook_time):
            self.total_time = (self.prep_time or 0) + (self.cook_time or 0)

        # Process image if uploaded
        if self.image and hasattr(self.image, "file"):
            from ..image_utils import process_recipe_image

            try:
                processed_image = process_recipe_image(self.image.file)
                if processed_image:
                    self.image = processed_image
            except Exception as e:
                print(f"Error processing recipe image: {str(e)}")

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("recipes:detail", kwargs={"slug": self.slug})

    @property
    def total_ingredients_count(self):
        """Total number of ingredients in this recipe."""
        return self.ingredients.count()

    @property
    def total_steps_count(self):
        """Total number of steps in this recipe."""
        return self.steps.count()

    @property
    def estimated_cost(self):
        """Estimated cost based on ingredient prices."""
        from inventory.models import Product

        total_cost = 0
        for ingredient in self.ingredients.all():
            if ingredient.product and ingredient.product.average_price:
                # Simple estimation - could be more sophisticated
                total_cost += float(ingredient.product.average_price)
        return total_cost

    def get_image_url(self, size="medium"):
        """Get recipe image URL with fallback."""
        from ..image_utils import get_recipe_image_url

        return get_recipe_image_url(self, size)

    def update_rating(self):
        """Update average rating and count from reviews."""
        reviews = self.reviews.all()
        if reviews.exists():
            self.rating_count = reviews.count()
            self.rating_average = (
                reviews.aggregate(avg=models.Avg("rating"))["avg"] or 0
            )
        else:
            self.rating_count = 0
            self.rating_average = 0
        self.save(update_fields=["rating_average", "rating_count"])