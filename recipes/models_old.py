from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
import uuid

User = get_user_model()


class RecipeCategory(models.Model):
    """
    Recipe categories (Italian, Mexican, Vegetarian, etc.).
    """

    name = models.CharField(_("name"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), unique=True)
    description = models.TextField(_("description"), blank=True)
    color = models.CharField(_("color"), max_length=7, default="#6B7280")
    icon = models.CharField(_("icon"), max_length=50, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    order = models.IntegerField(_("display order"), default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recipe_categories"
        verbose_name = _("recipe category")
        verbose_name_plural = _("recipe categories")
        ordering = ["order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class RecipeTag(models.Model):
    """
    Tags for recipes (quick, healthy, budget-friendly, etc.).
    """

    name = models.CharField(_("name"), max_length=50, unique=True)
    slug = models.SlugField(_("slug"), unique=True)
    description = models.TextField(_("description"), blank=True)
    color = models.CharField(_("color"), max_length=7, default="#6B7280")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recipe_tags"
        verbose_name = _("recipe tag")
        verbose_name_plural = _("recipe tags")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Convert name to lowercase
        self.name = self.name.lower()
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


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
    average_rating = models.DecimalField(
        _("average rating"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
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
            from .image_utils import process_recipe_image

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
        from .image_utils import get_recipe_image_url

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
        from fractions import Fraction

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
