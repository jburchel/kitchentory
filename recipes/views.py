from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import json
import re

from .models import (
    Recipe,
    RecipeCategory,
    RecipeTag,
    RecipeIngredient,
    RecipeStep,
    UserRecipeInteraction,
)
from .forms import (
    RecipeForm,
    RecipeIngredientFormSet,
    RecipeStepFormSet,
    RecipeImportForm,
    QuickRecipeForm,
    RecipeSearchForm,
)
from .utils import import_recipe_from_url, create_recipe_from_data
from subscriptions.decorators import feature_required, usage_limit_required, track_usage


@login_required
@feature_required('recipe_matching')
@track_usage('recipe_search')
def recipe_list(request):
    """
    Recipe discovery and search page.
    """
    form = RecipeSearchForm(request.GET or None)
    # Show public recipes AND user's own recipes
    recipes = (
        Recipe.objects.filter(Q(is_public=True) | Q(created_by=request.user))
        .select_related("category")
        .prefetch_related("tags")
    )

    # Apply search filters
    if form.is_valid():
        if form.cleaned_data.get("q"):
            query = form.cleaned_data["q"]
            recipes = recipes.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(ingredients__name__icontains=query)
            ).distinct()

        if form.cleaned_data.get("category"):
            recipes = recipes.filter(category=form.cleaned_data["category"])

        if form.cleaned_data.get("tags"):
            recipes = recipes.filter(tags__in=form.cleaned_data["tags"]).distinct()

        if form.cleaned_data.get("difficulty"):
            recipes = recipes.filter(difficulty=form.cleaned_data["difficulty"])

        if form.cleaned_data.get("max_time"):
            recipes = recipes.filter(total_time__lte=form.cleaned_data["max_time"])

        # Dietary restrictions
        dietary = form.cleaned_data.get("dietary_restrictions", [])
        if "vegetarian" in dietary:
            recipes = recipes.filter(is_vegetarian=True)
        if "vegan" in dietary:
            recipes = recipes.filter(is_vegan=True)
        if "gluten_free" in dietary:
            recipes = recipes.filter(is_gluten_free=True)
        if "dairy_free" in dietary:
            recipes = recipes.filter(is_dairy_free=True)
        if "nut_free" in dietary:
            recipes = recipes.filter(is_nut_free=True)

        if form.cleaned_data.get("min_rating"):
            recipes = recipes.filter(
                rating_average__gte=form.cleaned_data["min_rating"]
            )

    # Order by rating and creation date
    recipes = recipes.order_by("-rating_average", "-created_at")

    # Pagination
    paginator = Paginator(recipes, 12)  # 12 recipes per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "form": form,
        "recipes": page_obj,
        "categories": RecipeCategory.objects.filter(parent__isnull=True),
        "popular_tags": RecipeTag.objects.all()[:10],
    }

    return render(request, "recipes/list.html", context)


@login_required
def recipe_detail(request, slug):
    """
    Recipe detail view with ingredients and steps.
    """
    recipe = get_object_or_404(Recipe, slug=slug)

    # Check if user can view this recipe
    if not recipe.is_public and recipe.created_by != request.user:
        messages.error(request, _("You do not have permission to view this recipe."))
        return redirect("recipes:list")

    # Track view interaction
    if request.user.is_authenticated:
        UserRecipeInteraction.objects.get_or_create(
            user=request.user, recipe=recipe, interaction_type="view"
        )
        recipe.view_count += 1
        recipe.save(update_fields=["view_count"])

    # Get ingredients grouped by group
    ingredients = recipe.ingredients.all().order_by("order")
    ingredient_groups = {}
    for ingredient in ingredients:
        group = ingredient.group or "Main Ingredients"
        if group not in ingredient_groups:
            ingredient_groups[group] = []
        ingredient_groups[group].append(ingredient)

    # Get steps
    steps = recipe.steps.all().order_by("step_number")

    # Check user interactions
    user_interactions = {}
    if request.user.is_authenticated:
        interactions = UserRecipeInteraction.objects.filter(
            user=request.user, recipe=recipe
        ).values_list("interaction_type", flat=True)
        user_interactions = {interaction: True for interaction in interactions}

    context = {
        "recipe": recipe,
        "ingredient_groups": ingredient_groups,
        "steps": steps,
        "user_interactions": user_interactions,
        "can_edit": request.user == recipe.created_by,
    }

    return render(request, "recipes/detail.html", context)


@login_required
def recipe_create(request):
    """
    Create a new recipe with ingredients and steps.
    """
    if request.method == "POST":
        form = RecipeForm(request.POST, request.FILES, user=request.user)
        ingredient_formset = RecipeIngredientFormSet(request.POST, prefix="ingredients")
        step_formset = RecipeStepFormSet(request.POST, request.FILES, prefix="steps")

        if (
            form.is_valid()
            and ingredient_formset.is_valid()
            and step_formset.is_valid()
        ):
            recipe = form.save()

            # Save ingredients
            ingredients = ingredient_formset.save(commit=False)
            for i, ingredient in enumerate(ingredients):
                ingredient.recipe = recipe
                ingredient.order = i + 1
                ingredient.save()

            # Save steps
            steps = step_formset.save(commit=False)
            for i, step in enumerate(steps):
                step.recipe = recipe
                step.step_number = i + 1
                step.save()

            messages.success(request, _("Recipe created successfully!"))
            return redirect("recipes:detail", slug=recipe.slug)
    else:
        form = RecipeForm(user=request.user)
        ingredient_formset = RecipeIngredientFormSet(prefix="ingredients")
        step_formset = RecipeStepFormSet(prefix="steps")

    context = {
        "form": form,
        "ingredient_formset": ingredient_formset,
        "step_formset": step_formset,
        "title": "Create Recipe",
    }

    return render(request, "recipes/create.html", context)


@login_required
def recipe_edit(request, slug):
    """
    Edit an existing recipe.
    """
    recipe = get_object_or_404(Recipe, slug=slug)

    # Check permissions
    if recipe.created_by != request.user:
        messages.error(request, _("You can only edit your own recipes."))
        return redirect("recipes:detail", slug=recipe.slug)

    if request.method == "POST":
        form = RecipeForm(
            request.POST, request.FILES, instance=recipe, user=request.user
        )
        ingredient_formset = RecipeIngredientFormSet(
            request.POST, instance=recipe, prefix="ingredients"
        )
        step_formset = RecipeStepFormSet(
            request.POST, request.FILES, instance=recipe, prefix="steps"
        )

        if (
            form.is_valid()
            and ingredient_formset.is_valid()
            and step_formset.is_valid()
        ):
            recipe = form.save()

            # Save ingredients with proper ordering
            ingredients = ingredient_formset.save(commit=False)
            for ingredient in ingredient_formset.deleted_objects:
                ingredient.delete()
            for i, ingredient in enumerate(ingredients):
                ingredient.recipe = recipe
                ingredient.order = i + 1
                ingredient.save()

            # Save steps with proper ordering
            steps = step_formset.save(commit=False)
            for step in step_formset.deleted_objects:
                step.delete()
            for i, step in enumerate(steps):
                step.recipe = recipe
                step.step_number = i + 1
                step.save()

            messages.success(request, _("Recipe updated successfully!"))
            return redirect("recipes:detail", slug=recipe.slug)
    else:
        form = RecipeForm(instance=recipe, user=request.user)
        ingredient_formset = RecipeIngredientFormSet(
            instance=recipe, prefix="ingredients"
        )
        step_formset = RecipeStepFormSet(instance=recipe, prefix="steps")

    context = {
        "form": form,
        "ingredient_formset": ingredient_formset,
        "step_formset": step_formset,
        "recipe": recipe,
        "title": "Edit Recipe",
    }

    return render(request, "recipes/create.html", context)


@login_required
def recipe_quick_create(request):
    """
    Quick recipe creation with simple text input.
    """
    if request.method == "POST":
        form = QuickRecipeForm(request.POST)

        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.created_by = request.user

            # Auto-generate slug
            recipe.slug = slugify(recipe.title)
            counter = 1
            while Recipe.objects.filter(slug=recipe.slug).exists():
                recipe.slug = f"{slugify(recipe.title)}-{counter}"
                counter += 1

            recipe.save()
            form.save_m2m()

            # Parse and create ingredients
            ingredients_text = form.cleaned_data["ingredients_text"]
            for i, line in enumerate(ingredients_text.strip().split("\n")):
                line = line.strip()
                if line:
                    parsed = parse_ingredient_line(line)
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        order=i + 1,
                        name=parsed["name"],
                        quantity=parsed["quantity"],
                        unit=parsed["unit"],
                        preparation=parsed["preparation"],
                    )

            # Parse and create steps
            instructions_text = form.cleaned_data["instructions_text"]
            for i, line in enumerate(instructions_text.strip().split("\n")):
                line = line.strip()
                if line:
                    # Remove step numbering if present
                    step_text = re.sub(r"^\d+\.\s*", "", line)
                    RecipeStep.objects.create(
                        recipe=recipe, step_number=i + 1, instruction=step_text
                    )

            messages.success(request, _("Recipe created successfully!"))
            return redirect("recipes:detail", slug=recipe.slug)
    else:
        form = QuickRecipeForm()

    context = {
        "form": form,
        "title": "Quick Create Recipe",
    }

    return render(request, "recipes/quick_create.html", context)


@login_required
@feature_required('advanced_matching')
def recipe_import(request):
    """
    Import recipe from URL.
    """
    if request.method == "POST":
        form = RecipeImportForm(request.POST)

        if form.is_valid():
            url = form.cleaned_data["url"]
            make_public = form.cleaned_data["make_public"]

            try:
                # Import recipe from URL (implementation in next task)
                recipe_data = import_recipe_from_url(url)

                if recipe_data:
                    # Create recipe from imported data
                    recipe = create_recipe_from_data(
                        recipe_data, request.user, make_public
                    )
                    messages.success(request, _("Recipe imported successfully!"))
                    return redirect("recipes:detail", slug=recipe.slug)
                else:
                    messages.error(request, _("Could not import recipe from this URL."))
            except Exception as e:
                messages.error(request, _("Error importing recipe: {}").format(str(e)))
    else:
        form = RecipeImportForm()

    context = {
        "form": form,
        "title": "Import Recipe",
    }

    return render(request, "recipes/import.html", context)


@login_required
@require_http_methods(["POST"])
def recipe_like(request, slug):
    """
    Toggle like status for a recipe.
    """
    recipe = get_object_or_404(Recipe, slug=slug)

    interaction, created = UserRecipeInteraction.objects.get_or_create(
        user=request.user, recipe=recipe, interaction_type="like"
    )

    if not created:
        # Unlike - remove the interaction
        interaction.delete()
        liked = False
        recipe.like_count = max(0, recipe.like_count - 1)
    else:
        # Like
        liked = True
        recipe.like_count += 1

    recipe.save(update_fields=["like_count"])

    if request.headers.get("HX-Request"):
        # Return HTMX response
        context = {"recipe": recipe, "liked": liked}
        return render(request, "recipes/partials/like_button.html", context)

    return JsonResponse({"liked": liked, "like_count": recipe.like_count})


@login_required
def recipe_print(request, slug):
    """
    Print-friendly recipe view.
    """
    recipe = get_object_or_404(Recipe, slug=slug)

    # Check if user can view this recipe
    if not recipe.is_public and recipe.created_by != request.user:
        messages.error(request, _("You do not have permission to view this recipe."))
        return redirect("recipes:list")

    # Get ingredients grouped by group
    ingredients = recipe.ingredients.all().order_by("order")
    ingredient_groups = {}
    for ingredient in ingredients:
        group = ingredient.group or "Main Ingredients"
        if group not in ingredient_groups:
            ingredient_groups[group] = []
        ingredient_groups[group].append(ingredient)

    # Get steps
    steps = recipe.steps.all().order_by("step_number")

    context = {
        "recipe": recipe,
        "ingredient_groups": ingredient_groups,
        "steps": steps,
    }

    return render(request, "recipes/print.html", context)


# Helper functions for parsing and importing


def parse_ingredient_line(line):
    """
    Parse a single ingredient line into components.
    Basic parsing - can be enhanced with NLP libraries.
    """
    # Common units pattern
    units_pattern = r"\b(cups?|cup|tbsp|tablespoons?|tsp|teaspoons?|oz|ounces?|lbs?|pounds?|g|grams?|kg|kilograms?|ml|milliliters?|l|liters?|pinch|dash|cloves?|slices?)\b"

    # Try to extract quantity and unit
    quantity_match = re.search(r"^(\d+(?:\.\d+)?(?:/\d+)?)\s*", line)
    unit_match = re.search(units_pattern, line, re.IGNORECASE)

    quantity = None
    unit = ""
    name = line
    preparation = ""

    if quantity_match:
        quantity_str = quantity_match.group(1)
        # Handle fractions
        if "/" in quantity_str:
            parts = quantity_str.split("/")
            if len(parts) == 2:
                try:
                    quantity = float(parts[0]) / float(parts[1])
                except:
                    quantity = None
        else:
            try:
                quantity = float(quantity_str)
            except:
                quantity = None

        # Remove quantity from name
        name = line[quantity_match.end() :].strip()

    if unit_match:
        unit = unit_match.group(0).lower()
        # Normalize units
        unit_mapping = {
            "cup": "cup",
            "cups": "cup",
            "tablespoon": "tbsp",
            "tablespoons": "tbsp",
            "teaspoon": "tsp",
            "teaspoons": "tsp",
            "ounce": "oz",
            "ounces": "oz",
            "pound": "lb",
            "pounds": "lb",
            "lbs": "lb",
            "gram": "g",
            "grams": "g",
            "kilogram": "kg",
            "kilograms": "kg",
            "milliliter": "ml",
            "milliliters": "ml",
            "liter": "l",
            "liters": "l",
            "clove": "clove",
            "cloves": "clove",
            "slice": "slice",
            "slices": "slice",
        }
        unit = unit_mapping.get(unit, unit)

        # Remove unit from name
        name = re.sub(units_pattern, "", name, flags=re.IGNORECASE).strip()

    # Extract preparation (words in parentheses or after comma)
    prep_match = re.search(r"[,\(]([^,\)]+)[\),]?$", name)
    if prep_match:
        preparation = prep_match.group(1).strip()
        name = name[: prep_match.start()].strip()

    return {
        "quantity": quantity,
        "unit": unit,
        "name": name,
        "preparation": preparation,
    }


@login_required
def recipe_cooking(request, slug):
    """
    Cooking mode view for step-by-step recipe execution.
    """
    recipe = get_object_or_404(Recipe, slug=slug)

    # Check if user can view this recipe
    if not recipe.is_public and recipe.created_by != request.user:
        messages.error(request, _("You do not have permission to view this recipe."))
        return redirect("recipes:list")

    # Get all ingredients and steps
    ingredients = recipe.ingredients.all().order_by("order")
    steps = recipe.steps.all().order_by("step_number")

    context = {
        "recipe": recipe,
        "ingredients": ingredients,
        "steps": steps,
        "total_steps": steps.count(),
    }

    return render(request, "recipes/cooking/start.html", context)


# Import the functions from utils
from .utils import import_recipe_from_url, create_recipe_from_data
