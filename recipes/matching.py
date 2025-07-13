"""
Recipe matching engine for finding recipes based on available inventory.
"""

from django.db.models import Q, Count, Case, When, F, Value, IntegerField
from django.contrib.auth import get_user_model
from decimal import Decimal
import difflib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from .models import Recipe, RecipeIngredient
from inventory.models import InventoryItem, Product

User = get_user_model()


@dataclass
class IngredientMatch:
    """Represents how well a recipe ingredient matches user's inventory."""

    recipe_ingredient: RecipeIngredient
    inventory_item: Optional[InventoryItem]
    match_type: str  # 'exact', 'partial', 'substitute', 'missing'
    confidence: float  # 0.0 to 1.0
    quantity_ratio: float  # Available quantity / Required quantity
    notes: str = ""


@dataclass
class RecipeMatch:
    """Represents how well a recipe matches user's inventory."""

    recipe: Recipe
    overall_score: float  # 0.0 to 1.0
    ingredient_matches: List[IngredientMatch]
    missing_ingredients: List[RecipeIngredient]
    match_type: str  # 'perfect', 'almost', 'partial', 'impossible'
    cookable: bool
    missing_count: int
    substitution_count: int
    estimated_cost: Decimal


class RecipeMatchingEngine:
    """
    Core engine for matching recipes to user's available inventory.
    """

    # Ingredient substitution mapping
    SUBSTITUTIONS = {
        # Dairy substitutions
        "milk": ["almond milk", "soy milk", "oat milk", "coconut milk"],
        "butter": ["margarine", "coconut oil", "olive oil", "vegetable oil"],
        "heavy cream": ["coconut cream", "evaporated milk", "half and half"],
        "yogurt": ["greek yogurt", "sour cream", "cottage cheese"],
        # Flour substitutions
        "all-purpose flour": ["whole wheat flour", "bread flour", "cake flour"],
        "bread flour": ["all-purpose flour", "whole wheat flour"],
        # Sugar substitutions
        "white sugar": ["brown sugar", "coconut sugar", "honey", "maple syrup"],
        "brown sugar": ["white sugar", "coconut sugar", "honey"],
        # Oil substitutions
        "vegetable oil": ["canola oil", "sunflower oil", "safflower oil"],
        "olive oil": ["avocado oil", "vegetable oil", "canola oil"],
        # Vinegar substitutions
        "white vinegar": ["apple cider vinegar", "rice vinegar"],
        "apple cider vinegar": ["white vinegar", "white wine vinegar"],
        # Herb substitutions
        "fresh basil": ["dried basil", "fresh oregano", "fresh thyme"],
        "fresh parsley": ["dried parsley", "fresh cilantro", "fresh chives"],
        "fresh thyme": ["dried thyme", "fresh oregano", "fresh rosemary"],
        # Protein substitutions
        "chicken breast": ["chicken thigh", "turkey breast", "pork tenderloin"],
        "ground beef": ["ground turkey", "ground chicken", "ground pork"],
        # Vegetable substitutions
        "yellow onion": ["white onion", "red onion", "sweet onion"],
        "red bell pepper": [
            "yellow bell pepper",
            "orange bell pepper",
            "green bell pepper",
        ],
    }

    # Similarity threshold for fuzzy matching
    SIMILARITY_THRESHOLD = 0.7

    def __init__(self, user: User):
        self.user = user
        self.user_inventory = self._get_user_inventory()
        self.ingredient_name_mapping = self._build_ingredient_mapping()

    def _get_user_inventory(self) -> Dict[str, InventoryItem]:
        """Get user's current inventory as a name-mapped dictionary."""
        inventory = {}
        items = InventoryItem.objects.filter(
            user=self.user, current_quantity__gt=0
        ).select_related("product")

        for item in items:
            # Use product name as primary key
            if item.product:
                name = item.product.name.lower()
                inventory[name] = item

        return inventory

    def _build_ingredient_mapping(self) -> Dict[str, str]:
        """Build mapping of ingredient variations to standardized names."""
        mapping = {}

        # Add plurals and common variations
        for name in self.user_inventory.keys():
            # Add singular/plural variations
            if name.endswith("s") and len(name) > 3:
                singular = name[:-1]
                mapping[singular] = name
            else:
                plural = name + "s"
                mapping[plural] = name

            # Add variations without articles
            for article in ["the ", "a ", "an "]:
                if name.startswith(article):
                    without_article = name[len(article) :]
                    mapping[without_article] = name

        return mapping

    def find_matching_recipes(
        self,
        limit: int = 20,
        dietary_filters: Optional[Dict[str, bool]] = None,
        max_missing: int = 3,
        include_almost_matches: bool = True,
    ) -> List[RecipeMatch]:
        """
        Find recipes that match user's available inventory.

        Args:
            limit: Maximum number of recipes to return
            dietary_filters: Dict of dietary restrictions (vegetarian, vegan, etc.)
            max_missing: Maximum number of missing ingredients to allow
            include_almost_matches: Whether to include recipes with missing ingredients

        Returns:
            List of RecipeMatch objects sorted by match score
        """
        # Start with public recipes
        recipes = Recipe.objects.filter(is_public=True).prefetch_related(
            "ingredients__product", "category", "tags"
        )

        # Apply dietary filters
        if dietary_filters:
            if dietary_filters.get("vegetarian"):
                recipes = recipes.filter(is_vegetarian=True)
            if dietary_filters.get("vegan"):
                recipes = recipes.filter(is_vegan=True)
            if dietary_filters.get("gluten_free"):
                recipes = recipes.filter(is_gluten_free=True)
            if dietary_filters.get("dairy_free"):
                recipes = recipes.filter(is_dairy_free=True)
            if dietary_filters.get("nut_free"):
                recipes = recipes.filter(is_nut_free=True)

        # Calculate matches for each recipe
        recipe_matches = []
        for recipe in recipes[: limit * 2]:  # Get extra to account for filtering
            match = self._calculate_recipe_match(recipe)

            # Filter based on criteria
            if match.missing_count <= max_missing:
                if match.cookable or include_almost_matches:
                    recipe_matches.append(match)

        # Sort by match score and return top results
        recipe_matches.sort(key=lambda x: x.overall_score, reverse=True)
        return recipe_matches[:limit]

    def _calculate_recipe_match(self, recipe: Recipe) -> RecipeMatch:
        """Calculate how well a recipe matches user's inventory."""
        ingredients = recipe.ingredients.all()
        ingredient_matches = []
        missing_ingredients = []
        missing_count = 0
        substitution_count = 0
        total_score = 0.0
        estimated_cost = Decimal("0.00")

        for recipe_ingredient in ingredients:
            match = self._match_ingredient(recipe_ingredient)
            ingredient_matches.append(match)

            if match.match_type == "missing":
                missing_ingredients.append(recipe_ingredient)
                missing_count += 1
                # Estimate cost for missing ingredient
                if (
                    recipe_ingredient.product
                    and recipe_ingredient.product.average_price
                ):
                    estimated_cost += recipe_ingredient.product.average_price
                else:
                    estimated_cost += Decimal("3.00")  # Default estimate
            elif match.match_type == "substitute":
                substitution_count += 1

            # Weight optional ingredients less
            weight = 0.5 if recipe_ingredient.is_optional else 1.0
            total_score += match.confidence * weight

        # Calculate overall score
        total_weight = sum(0.5 if ing.is_optional else 1.0 for ing in ingredients)
        overall_score = total_score / total_weight if total_weight > 0 else 0.0

        # Determine match type and cookability
        if missing_count == 0:
            match_type = "perfect"
            cookable = True
        elif missing_count <= 2 and all(ing.is_optional for ing in missing_ingredients):
            match_type = "almost"
            cookable = True
        elif missing_count <= 3:
            match_type = "partial"
            cookable = False
        else:
            match_type = "impossible"
            cookable = False

        return RecipeMatch(
            recipe=recipe,
            overall_score=overall_score,
            ingredient_matches=ingredient_matches,
            missing_ingredients=missing_ingredients,
            match_type=match_type,
            cookable=cookable,
            missing_count=missing_count,
            substitution_count=substitution_count,
            estimated_cost=estimated_cost,
        )

    def _match_ingredient(self, recipe_ingredient: RecipeIngredient) -> IngredientMatch:
        """Match a single recipe ingredient against user's inventory."""
        ingredient_name = recipe_ingredient.name.lower().strip()

        # Try exact match first
        if ingredient_name in self.user_inventory:
            inventory_item = self.user_inventory[ingredient_name]
            quantity_ratio = self._calculate_quantity_ratio(
                recipe_ingredient, inventory_item
            )

            return IngredientMatch(
                recipe_ingredient=recipe_ingredient,
                inventory_item=inventory_item,
                match_type="exact",
                confidence=1.0,
                quantity_ratio=quantity_ratio,
                notes="Exact match found",
            )

        # Try mapped variations
        mapped_name = self.ingredient_name_mapping.get(ingredient_name)
        if mapped_name and mapped_name in self.user_inventory:
            inventory_item = self.user_inventory[mapped_name]
            quantity_ratio = self._calculate_quantity_ratio(
                recipe_ingredient, inventory_item
            )

            return IngredientMatch(
                recipe_ingredient=recipe_ingredient,
                inventory_item=inventory_item,
                match_type="exact",
                confidence=0.95,
                quantity_ratio=quantity_ratio,
                notes="Matched variation",
            )

        # Try fuzzy matching
        best_match = self._fuzzy_match_ingredient(ingredient_name)
        if best_match:
            inventory_item = self.user_inventory[best_match["name"]]
            quantity_ratio = self._calculate_quantity_ratio(
                recipe_ingredient, inventory_item
            )

            return IngredientMatch(
                recipe_ingredient=recipe_ingredient,
                inventory_item=inventory_item,
                match_type="partial",
                confidence=best_match["confidence"],
                quantity_ratio=quantity_ratio,
                notes=f"Fuzzy match: {best_match['name']}",
            )

        # Try substitution matching
        substitute_match = self._find_substitution(ingredient_name)
        if substitute_match:
            inventory_item = self.user_inventory[substitute_match["name"]]
            quantity_ratio = self._calculate_quantity_ratio(
                recipe_ingredient, inventory_item
            )

            return IngredientMatch(
                recipe_ingredient=recipe_ingredient,
                inventory_item=inventory_item,
                match_type="substitute",
                confidence=substitute_match["confidence"],
                quantity_ratio=quantity_ratio,
                notes=f"Substitute: {substitute_match['name']}",
            )

        # No match found
        return IngredientMatch(
            recipe_ingredient=recipe_ingredient,
            inventory_item=None,
            match_type="missing",
            confidence=0.0,
            quantity_ratio=0.0,
            notes="Ingredient not available",
        )

    def _fuzzy_match_ingredient(self, ingredient_name: str) -> Optional[Dict]:
        """Find the best fuzzy match for an ingredient."""
        best_match = None
        best_score = 0.0

        for inventory_name in self.user_inventory.keys():
            # Calculate similarity
            similarity = difflib.SequenceMatcher(
                None, ingredient_name, inventory_name
            ).ratio()

            # Also check if one contains the other
            if ingredient_name in inventory_name or inventory_name in ingredient_name:
                similarity = max(similarity, 0.8)

            if similarity > best_score and similarity >= self.SIMILARITY_THRESHOLD:
                best_score = similarity
                best_match = {"name": inventory_name, "confidence": similarity}

        return best_match

    def _find_substitution(self, ingredient_name: str) -> Optional[Dict]:
        """Find a suitable substitution for an ingredient."""
        # Check if we have substitutes for this ingredient
        substitutes = self.SUBSTITUTIONS.get(ingredient_name, [])

        for substitute in substitutes:
            if substitute.lower() in self.user_inventory:
                return {
                    "name": substitute.lower(),
                    "confidence": 0.7,  # Substitutions get lower confidence
                }

        # Check reverse substitutions (if ingredient is a substitute for something we have)
        for base_ingredient, sub_list in self.SUBSTITUTIONS.items():
            if ingredient_name in [s.lower() for s in sub_list]:
                if base_ingredient.lower() in self.user_inventory:
                    return {"name": base_ingredient.lower(), "confidence": 0.7}

        return None

    def _calculate_quantity_ratio(
        self, recipe_ingredient: RecipeIngredient, inventory_item: InventoryItem
    ) -> float:
        """Calculate how much of the required quantity is available."""
        if not recipe_ingredient.quantity or recipe_ingredient.quantity <= 0:
            return 1.0  # If no specific quantity required, assume we have enough

        if not inventory_item.quantity or inventory_item.quantity <= 0:
            return 0.0

        # Simple ratio calculation (could be enhanced with unit conversion)
        required = float(recipe_ingredient.quantity)
        available = float(inventory_item.quantity)

        return min(
            available / required, 2.0
        )  # Cap at 2.0 to indicate "more than enough"

    def get_exact_matches(self) -> List[RecipeMatch]:
        """Get recipes that can be made with exact ingredient matches."""
        matches = self.find_matching_recipes(include_almost_matches=False)
        return [match for match in matches if match.match_type == "perfect"]

    def get_almost_matches(self, max_missing: int = 2) -> List[RecipeMatch]:
        """Get recipes that are almost cookable (missing few ingredients)."""
        matches = self.find_matching_recipes(max_missing=max_missing)
        return [match for match in matches if match.match_type in ["almost", "partial"]]


def get_recipe_recommendations(user: User, limit: int = 10) -> List[RecipeMatch]:
    """
    Get recipe recommendations for a user based on their inventory.

    This is the main entry point for recipe matching.
    """
    engine = RecipeMatchingEngine(user)
    return engine.find_matching_recipes(limit=limit)


def check_recipe_cookability(user: User, recipe: Recipe) -> RecipeMatch:
    """
    Check if a specific recipe can be cooked with user's current inventory.
    """
    engine = RecipeMatchingEngine(user)
    return engine._calculate_recipe_match(recipe)
