from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator
from django.forms import formset_factory, inlineformset_factory
from .models import Recipe, RecipeIngredient, RecipeStep, RecipeCategory, RecipeTag
import re


class RecipeForm(forms.ModelForm):
    """
    Main recipe creation/editing form.
    """

    class Meta:
        model = Recipe
        fields = [
            "title",
            "description",
            "category",
            "tags",
            "prep_time",
            "cook_time",
            "difficulty",
            "servings",
            "serving_unit",
            "calories_per_serving",
            "protein_grams",
            "carb_grams",
            "fat_grams",
            "image",
            "image_url",
            "video_url",
            "source_name",
            "source_url",
            "author",
            "is_public",
            "is_vegetarian",
            "is_vegan",
            "is_gluten_free",
            "is_dairy_free",
            "is_nut_free",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter recipe title...",
                    "maxlength": 200,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "Describe your recipe...",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "tags": forms.CheckboxSelectMultiple(
                attrs={"class": "form-checkbox-group"}
            ),
            "prep_time": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Minutes", "min": 0}
            ),
            "cook_time": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Minutes", "min": 0}
            ),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
            "servings": forms.NumberInput(
                attrs={"class": "form-input", "min": 1, "value": 4}
            ),
            "serving_unit": forms.Select(attrs={"class": "form-select"}),
            "calories_per_serving": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Optional", "min": 0}
            ),
            "protein_grams": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Optional",
                    "min": 0,
                    "step": 0.1,
                }
            ),
            "carb_grams": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Optional",
                    "min": 0,
                    "step": 0.1,
                }
            ),
            "fat_grams": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Optional",
                    "min": 0,
                    "step": 0.1,
                }
            ),
            "image": forms.FileInput(
                attrs={"class": "form-file-input", "accept": "image/*"}
            ),
            "image_url": forms.URLInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "https://example.com/image.jpg",
                }
            ),
            "video_url": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "YouTube, Vimeo, etc."}
            ),
            "source_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "e.g., Food Network, Grandma's Recipe",
                }
            ),
            "source_url": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "Original recipe URL"}
            ),
            "author": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Recipe author"}
            ),
            "is_public": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_vegetarian": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_vegan": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_gluten_free": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_dairy_free": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_nut_free": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

        labels = {
            "prep_time": _("Preparation Time (minutes)"),
            "cook_time": _("Cooking Time (minutes)"),
            "calories_per_serving": _("Calories per Serving"),
            "protein_grams": _("Protein (grams)"),
            "carb_grams": _("Carbohydrates (grams)"),
            "fat_grams": _("Fat (grams)"),
            "image_url": _("Image URL"),
            "video_url": _("Video URL"),
            "source_name": _("Source Name"),
            "source_url": _("Source URL"),
            "is_public": _("Make this recipe public"),
            "is_vegetarian": _("Vegetarian"),
            "is_vegan": _("Vegan"),
            "is_gluten_free": _("Gluten-free"),
            "is_dairy_free": _("Dairy-free"),
            "is_nut_free": _("Nut-free"),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter categories to only show top-level categories for better UX
        self.fields["category"].queryset = RecipeCategory.objects.filter(
            parent__isnull=True
        )

        # Group tags by type for better organization
        self.fields["tags"].queryset = RecipeTag.objects.all().order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        prep_time = cleaned_data.get("prep_time")
        cook_time = cleaned_data.get("cook_time")

        # Ensure at least one time is provided
        if not prep_time and not cook_time:
            raise forms.ValidationError(
                _("Please provide either preparation time, cooking time, or both.")
            )

        # Auto-calculate total time
        if prep_time or cook_time:
            cleaned_data["total_time"] = (prep_time or 0) + (cook_time or 0)

        return cleaned_data

    def clean_image(self):
        """Validate uploaded image."""
        image = self.cleaned_data.get("image")
        if image:
            from .image_utils import validate_recipe_image

            errors = validate_recipe_image(image)
            if errors:
                raise forms.ValidationError(errors)
        return image

    def save(self, commit=True):
        recipe = super().save(commit=False)

        # Set the creator
        if self.user:
            recipe.created_by = self.user

        # Auto-generate slug if not provided
        if not recipe.slug:
            from django.utils.text import slugify

            base_slug = slugify(recipe.title)
            recipe.slug = base_slug

            # Ensure unique slug
            counter = 1
            while Recipe.objects.filter(slug=recipe.slug).exists():
                recipe.slug = f"{base_slug}-{counter}"
                counter += 1

        if commit:
            recipe.save()
            self.save_m2m()  # Save many-to-many relationships

        return recipe


class RecipeIngredientForm(forms.ModelForm):
    """
    Form for individual recipe ingredients.
    """

    class Meta:
        model = RecipeIngredient
        fields = [
            "name",
            "quantity",
            "unit",
            "preparation",
            "group",
            "is_optional",
            "is_garnish",
            "notes",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "e.g., large onion, fresh basil",
                    "required": True,
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-input w-20",
                    "placeholder": "1",
                    "step": 0.25,
                    "min": 0,
                }
            ),
            "unit": forms.Select(attrs={"class": "form-select w-32"}),
            "preparation": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "diced, chopped, minced...",
                }
            ),
            "group": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "For the sauce, For topping...",
                }
            ),
            "is_optional": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_garnish": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 2,
                    "placeholder": "Substitution notes, special instructions...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True


class RecipeStepForm(forms.ModelForm):
    """
    Form for individual recipe steps.
    """

    class Meta:
        model = RecipeStep
        fields = [
            "title",
            "instruction",
            "step_type",
            "time_minutes",
            "temperature",
            "temperature_unit",
            "equipment_needed",
            "image",
            "video_url",
            "tips",
            "is_critical",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Optional step title"}
            ),
            "instruction": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "Detailed step instruction...",
                    "required": True,
                }
            ),
            "step_type": forms.Select(attrs={"class": "form-select w-32"}),
            "time_minutes": forms.NumberInput(
                attrs={"class": "form-input w-20", "placeholder": "Min", "min": 0}
            ),
            "temperature": forms.NumberInput(
                attrs={"class": "form-input w-20", "placeholder": "180"}
            ),
            "temperature_unit": forms.Select(attrs={"class": "form-select w-16"}),
            "equipment_needed": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "large skillet, food processor...",
                }
            ),
            "image": forms.FileInput(
                attrs={"class": "form-file-input", "accept": "image/*"}
            ),
            "video_url": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "Optional step video URL"}
            ),
            "tips": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 2,
                    "placeholder": "Tips and troubleshooting notes...",
                }
            ),
            "is_critical": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instruction"].required = True


# Create formsets for dynamic ingredient and step management
RecipeIngredientFormSet = inlineformset_factory(
    Recipe,
    RecipeIngredient,
    form=RecipeIngredientForm,
    extra=3,  # Show 3 empty forms by default
    can_delete=True,
    can_order=True,
)

RecipeStepFormSet = inlineformset_factory(
    Recipe,
    RecipeStep,
    form=RecipeStepForm,
    extra=2,  # Show 2 empty forms by default
    can_delete=True,
    can_order=True,
)


class RecipeImportForm(forms.Form):
    """
    Form for importing recipes from URLs.
    """

    # Popular recipe URLs for quick selection
    POPULAR_RECIPES = [
        ("", _("Choose a popular recipe...")),
        # Budget Bytes (Free, scraping-friendly)
        (
            "https://www.budgetbytes.com/one-pot-creamy-cajun-chicken-pasta/",
            "Creamy Cajun Chicken Pasta - Budget Bytes",
        ),
        (
            "https://www.budgetbytes.com/hearty-black-bean-quesadillas/",
            "Hearty Black Bean Quesadillas - Budget Bytes",
        ),
        (
            "https://www.budgetbytes.com/dragon-noodles/",
            "Dragon Noodles - Budget Bytes",
        ),
        # Food.com (Community recipes)
        (
            "https://www.food.com/recipe/creamy-chicken-and-rice-casserole-87376",
            "Lemony Chicken - Food.com",
        ),
        (
            "https://www.food.com/recipe/chicken-teriyaki-stir-fry-356351",
            "Memphis Dry Rub Ribs - Food.com",
        ),
        # King Arthur Baking (Trusted baking recipes)
        (
            "https://www.kingarthurbaking.com/recipes/classic-chocolate-chip-cookies-recipe",
            "Classic Chocolate Chip Cookies - King Arthur",
        ),
        (
            "https://www.kingarthurbaking.com/recipes/banana-bread-recipe",
            "Banana Bread - King Arthur",
        ),
        # Sally\'s Baking Addiction (Popular baking blog)
        (
            "https://sallysbakingaddiction.com/chocolate-chip-cookies/",
            "Best Soft Chocolate Chip Cookies - Sally's Baking",
        ),
        # Bon Appétit (Professional recipes)
        (
            "https://www.bonappetit.com/recipe/chocolate-chip-cookies",
            "Chocolate Chip Cookies - Bon Appétit",
        ),
        (
            "https://www.bonappetit.com/recipe/banana-bread",
            "BA's Best Banana Bread - Bon Appétit",
        ),
        # Food52 (Community-driven)
        (
            "https://food52.com/recipes/23250-chocolate-chip-cookies",
            "Aunt Mary's Tomato Tart - Food52",
        ),
        (
            "https://food52.com/recipes/14469-banana-bread",
            "Corn Chowder (Vegan) - Food52",
        ),
        # NYT Cooking (Premium quality)
        (
            "https://cooking.nytimes.com/recipes/1016062-chocolate-chip-cookies",
            "Red Lentil Soup - NYT Cooking",
        ),
        (
            "https://cooking.nytimes.com/recipes/1018529-classic-meatballs",
            "Coq au Vin - NYT Cooking",
        ),
        ("custom_url", _("Enter custom URL...")),
    ]

    popular_recipe = forms.ChoiceField(
        label=_("Popular Recipes"),
        choices=POPULAR_RECIPES,
        required=False,
        widget=forms.Select(
            attrs={"class": "form-select", "id": "popular-recipe-select"}
        ),
        help_text=_(
            'Select a popular recipe to import, or choose "Enter custom URL" to input your own'
        ),
    )

    url = forms.URLField(
        label=_("Recipe URL"),
        required=False,
        widget=forms.URLInput(
            attrs={
                "class": "form-input",
                "placeholder": "https://example.com/recipe",
                "id": "custom-url-input",
                "style": "display: none;",
            }
        ),
        help_text=_("Enter a URL from a supported recipe website"),
    )

    make_public = forms.BooleanField(
        label=_("Make this recipe public"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        popular_recipe = cleaned_data.get("popular_recipe")
        url = cleaned_data.get("url")

        # Determine which URL to use
        final_url = None

        if popular_recipe and popular_recipe != "custom_url":
            # Use the selected popular recipe URL
            final_url = popular_recipe
        elif popular_recipe == "custom_url" and url:
            # Use the custom URL input
            final_url = url
        elif not popular_recipe and url:
            # Allow direct URL input if no popular recipe selected
            final_url = url
        else:
            raise forms.ValidationError(
                _("Please select a popular recipe or enter a custom URL.")
            )

        # Validate the final URL
        if final_url:
            validator = URLValidator()
            try:
                validator(final_url)
            except forms.ValidationError:
                raise forms.ValidationError(_("Please enter a valid URL."))

            # Store the final URL in cleaned_data
            cleaned_data["url"] = final_url

        return cleaned_data


class QuickRecipeForm(forms.ModelForm):
    """
    Simplified form for quick recipe creation.
    """

    ingredients_text = forms.CharField(
        label=_("Ingredients"),
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 6,
                "placeholder": "Enter ingredients, one per line:\n2 cups flour\n1 tsp salt\n3 eggs\n...",
            }
        ),
        help_text=_("Enter ingredients one per line with quantities"),
    )

    instructions_text = forms.CharField(
        label=_("Instructions"),
        widget=forms.Textarea(
            attrs={
                "class": "form-textarea",
                "rows": 8,
                "placeholder": "Enter cooking steps, one per line:\n1. Preheat oven to 350°F\n2. Mix flour and salt\n3. Add eggs and mix well\n...",
            }
        ),
        help_text=_("Enter cooking steps one per line"),
    )

    class Meta:
        model = Recipe
        fields = [
            "title",
            "description",
            "category",
            "prep_time",
            "cook_time",
            "servings",
            "difficulty",
            "is_public",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Recipe title",
                    "required": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "Brief description of the recipe",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "prep_time": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Minutes"}
            ),
            "cook_time": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Minutes"}
            ),
            "servings": forms.NumberInput(
                attrs={"class": "form-input", "value": 4, "min": 1}
            ),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = RecipeCategory.objects.filter(
            parent__isnull=True
        )
        self.fields["title"].required = True
        self.fields["ingredients_text"].required = True
        self.fields["instructions_text"].required = True


class RecipeSearchForm(forms.Form):
    """
    Form for recipe search and filtering.
    """

    q = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "Search recipes...",
                "autocomplete": "off",
            }
        ),
    )

    category = forms.ModelChoiceField(
        label=_("Category"),
        queryset=RecipeCategory.objects.all(),
        required=False,
        empty_label=_("All Categories"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    tags = forms.ModelMultipleChoiceField(
        label=_("Tags"),
        queryset=RecipeTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-checkbox-group"}),
    )

    difficulty = forms.ChoiceField(
        label=_("Difficulty"),
        choices=[("", _("Any Difficulty"))] + list(Recipe.DIFFICULTY_CHOICES),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    max_time = forms.IntegerField(
        label=_("Max Cooking Time (minutes)"),
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "placeholder": "Minutes", "min": 0}
        ),
    )

    dietary_restrictions = forms.MultipleChoiceField(
        label=_("Dietary Restrictions"),
        choices=[
            ("vegetarian", _("Vegetarian")),
            ("vegan", _("Vegan")),
            ("gluten_free", _("Gluten-free")),
            ("dairy_free", _("Dairy-free")),
            ("nut_free", _("Nut-free")),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-checkbox-group"}),
    )

    min_rating = forms.DecimalField(
        label=_("Minimum Rating"),
        required=False,
        min_value=0,
        max_value=5,
        decimal_places=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-input",
                "placeholder": "4.0",
                "step": 0.5,
                "min": 0,
                "max": 5,
            }
        ),
    )
