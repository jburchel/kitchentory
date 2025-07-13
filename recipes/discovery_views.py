"""
Views for recipe discovery and matching functionality.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
import json

from .models import Recipe, RecipeCategory, RecipeTag
from .matching import (
    RecipeMatchingEngine,
    get_recipe_recommendations,
    check_recipe_cookability,
)
from inventory.models import InventoryItem


@login_required
def discovery_dashboard(request):
    """
    Recipe discovery dashboard showing matches based on user's inventory.
    """
    # Get user's inventory count for display
    inventory_count = InventoryItem.objects.filter(
        user=request.user, current_quantity__gt=0
    ).count()

    # Get recipe recommendations
    recommendations = get_recipe_recommendations(request.user, limit=12)

    # Separate by match type
    perfect_matches = [r for r in recommendations if r.match_type == "perfect"]
    almost_matches = [
        r for r in recommendations if r.match_type in ["almost", "partial"]
    ]

    # Get categories and tags for filtering
    categories = RecipeCategory.objects.filter(parent__isnull=True)
    popular_tags = RecipeTag.objects.all()[:10]

    context = {
        "inventory_count": inventory_count,
        "perfect_matches": perfect_matches,
        "almost_matches": almost_matches,
        "total_recommendations": len(recommendations),
        "categories": categories,
        "popular_tags": popular_tags,
    }

    return render(request, "recipes/discovery/dashboard.html", context)


@login_required
def recipe_matches(request):
    """
    AJAX endpoint for getting recipe matches with filtering.
    """
    # Get filter parameters
    match_type = request.GET.get("match_type", "all")  # all, perfect, almost, partial
    category_id = request.GET.get("category")
    max_missing = int(request.GET.get("max_missing", 3))
    dietary_filters = {}

    # Parse dietary filters
    for filter_name in ["vegetarian", "vegan", "gluten_free", "dairy_free", "nut_free"]:
        if request.GET.get(filter_name) == "1":
            dietary_filters[filter_name] = True

    # Get matching engine
    engine = RecipeMatchingEngine(request.user)

    # Apply category filter if specified
    if category_id:
        recipes = Recipe.objects.filter(
            is_public=True, category_id=category_id
        ).prefetch_related("ingredients__product", "category", "tags")

        # Calculate matches for filtered recipes
        matches = []
        for recipe in recipes:
            match = engine._calculate_recipe_match(recipe)
            if match.missing_count <= max_missing:
                matches.append(match)
    else:
        # Get all matches
        matches = engine.find_matching_recipes(
            limit=50,
            dietary_filters=dietary_filters,
            max_missing=max_missing,
            include_almost_matches=True,
        )

    # Filter by match type
    if match_type == "perfect":
        matches = [m for m in matches if m.match_type == "perfect"]
    elif match_type == "almost":
        matches = [m for m in matches if m.match_type in ["almost", "partial"]]
    elif match_type == "missing":
        matches = [m for m in matches if m.missing_count > 0]

    # Prepare response data
    results = []
    for match in matches:
        results.append(
            {
                "recipe": {
                    "id": str(match.recipe.id),
                    "title": match.recipe.title,
                    "slug": match.recipe.slug,
                    "image_url": match.recipe.get_image_url(),
                    "prep_time": match.recipe.prep_time,
                    "cook_time": match.recipe.cook_time,
                    "difficulty": match.recipe.get_difficulty_display(),
                    "rating_average": float(match.recipe.rating_average),
                    "category": (
                        match.recipe.category.name if match.recipe.category else None
                    ),
                },
                "match": {
                    "score": round(match.overall_score * 100),
                    "type": match.match_type,
                    "cookable": match.cookable,
                    "missing_count": match.missing_count,
                    "substitution_count": match.substitution_count,
                    "estimated_cost": float(match.estimated_cost),
                },
                "missing_ingredients": [
                    {
                        "name": ing.name,
                        "quantity": ing.quantity,
                        "unit": ing.get_unit_display() if ing.unit else "",
                        "is_optional": ing.is_optional,
                    }
                    for ing in match.missing_ingredients
                ],
            }
        )

    return JsonResponse({"matches": results, "total": len(results)})


@login_required
def check_recipe_match(request, slug):
    """
    Check how well a specific recipe matches user's inventory.
    """
    recipe = get_object_or_404(Recipe, slug=slug)
    match = check_recipe_cookability(request.user, recipe)

    # Prepare detailed match information
    ingredient_details = []
    for ing_match in match.ingredient_matches:
        ingredient_details.append(
            {
                "recipe_ingredient": {
                    "name": ing_match.recipe_ingredient.name,
                    "quantity": ing_match.recipe_ingredient.quantity,
                    "unit": (
                        ing_match.recipe_ingredient.get_unit_display()
                        if ing_match.recipe_ingredient.unit
                        else ""
                    ),
                    "is_optional": ing_match.recipe_ingredient.is_optional,
                },
                "match": {
                    "type": ing_match.match_type,
                    "confidence": round(ing_match.confidence * 100),
                    "quantity_ratio": round(ing_match.quantity_ratio, 2),
                    "notes": ing_match.notes,
                    "available": ing_match.inventory_item is not None,
                },
                "inventory_item": (
                    {
                        "quantity": (
                            float(ing_match.inventory_item.quantity)
                            if ing_match.inventory_item
                            else 0
                        ),
                        "unit": (
                            ing_match.inventory_item.unit
                            if ing_match.inventory_item
                            else ""
                        ),
                    }
                    if ing_match.inventory_item
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "recipe": {
                "id": str(recipe.id),
                "title": recipe.title,
                "slug": recipe.slug,
            },
            "match": {
                "score": round(match.overall_score * 100),
                "type": match.match_type,
                "cookable": match.cookable,
                "missing_count": match.missing_count,
                "substitution_count": match.substitution_count,
                "estimated_cost": float(match.estimated_cost),
            },
            "ingredients": ingredient_details,
        }
    )


@login_required
def almost_there_recipes(request):
    """
    Show recipes that user is "almost there" - missing just a few ingredients.
    """
    engine = RecipeMatchingEngine(request.user)

    # Get recipes missing 1-3 ingredients
    almost_matches = engine.get_almost_matches(max_missing=3)

    # Group by number of missing ingredients
    missing_1 = [m for m in almost_matches if m.missing_count == 1]
    missing_2 = [m for m in almost_matches if m.missing_count == 2]
    missing_3 = [m for m in almost_matches if m.missing_count == 3]

    # Calculate total estimated cost for missing ingredients
    total_cost_1 = sum(m.estimated_cost for m in missing_1)
    total_cost_2 = sum(m.estimated_cost for m in missing_2)
    total_cost_3 = sum(m.estimated_cost for m in missing_3)

    context = {
        "missing_1": missing_1,
        "missing_2": missing_2,
        "missing_3": missing_3,
        "total_cost_1": total_cost_1,
        "total_cost_2": total_cost_2,
        "total_cost_3": total_cost_3,
        "total_recipes": len(almost_matches),
    }

    return render(request, "recipes/discovery/almost_there.html", context)


@login_required
@require_http_methods(["POST"])
def add_missing_to_shopping_list(request):
    """
    Add missing ingredients from a recipe to shopping list.
    """
    from shopping.models import ShoppingList, ShoppingListItem
    from shopping.utils import create_recipe_shopping_list
    from decimal import Decimal

    data = json.loads(request.body)
    recipe_slug = data.get("recipe_slug")
    list_id = data.get("list_id")  # Optional: add to specific list

    if not recipe_slug:
        return JsonResponse({"error": "Recipe slug required"}, status=400)

    recipe = get_object_or_404(Recipe, slug=recipe_slug)
    match = check_recipe_cookability(request.user, recipe)

    # Get or create shopping list
    if list_id:
        try:
            shopping_list = ShoppingList.objects.get(
                id=list_id, created_by=request.user, status__in=["active", "shopping"]
            )
        except ShoppingList.DoesNotExist:
            return JsonResponse({"error": "Shopping list not found"}, status=404)
    else:
        # Get active shopping list or create new one
        shopping_list = ShoppingList.objects.filter(
            created_by=request.user, status="active"
        ).first()

        if not shopping_list:
            shopping_list = ShoppingList.objects.create(
                name=f"Missing for {recipe.title}",
                description=f"Missing ingredients for cooking {recipe.title}",
                created_by=request.user,
                generation_source="recipe",
            )

    # Add missing ingredients to shopping list
    added_items = []
    for ingredient in match.missing_ingredients:
        # Check if item already exists in the list
        existing_item = shopping_list.items.filter(
            product=ingredient.product if hasattr(ingredient, "product") else None,
            name__iexact=ingredient.name,
            is_purchased=False,
        ).first()

        if not existing_item:
            shopping_item = ShoppingListItem.objects.create(
                shopping_list=shopping_list,
                product=ingredient.product if hasattr(ingredient, "product") else None,
                name=ingredient.name,
                quantity=(
                    Decimal(str(ingredient.quantity))
                    if ingredient.quantity
                    else Decimal("1.0")
                ),
                unit=ingredient.unit,
                category=ingredient.category if hasattr(ingredient, "category") else "",
                priority="high",
                added_by=request.user,
                source_recipe=recipe,
                notes=f"Missing ingredient for {recipe.title}",
            )

            added_items.append(
                {
                    "id": shopping_item.id,
                    "name": ingredient.name,
                    "quantity": float(shopping_item.quantity),
                    "unit": (
                        ingredient.get_unit_display()
                        if hasattr(ingredient, "get_unit_display")
                        else ingredient.unit
                    ),
                }
            )

    # Update shopping list totals
    shopping_list.calculate_estimated_total()

    return JsonResponse(
        {
            "success": True,
            "added_items": added_items,
            "shopping_list": {
                "id": str(shopping_list.id),
                "name": shopping_list.name,
                "total_items": shopping_list.total_items,
            },
            "message": f"Added {len(added_items)} missing ingredients to shopping list",
        }
    )


@login_required
def ingredient_substitutions(request):
    """
    Show available ingredient substitutions for recipes.
    """
    engine = RecipeMatchingEngine(request.user)

    # Get user's available ingredients
    user_inventory = engine.user_inventory

    # Find recipes with substitutions
    recommendations = engine.find_matching_recipes(limit=20)
    recipes_with_substitutions = [
        r for r in recommendations if r.substitution_count > 0
    ]

    context = {
        "recipes_with_substitutions": recipes_with_substitutions,
        "user_ingredients": list(user_inventory.keys()),
        "substitution_map": engine.SUBSTITUTIONS,
    }

    return render(request, "recipes/discovery/substitutions.html", context)
