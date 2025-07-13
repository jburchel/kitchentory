"""
Recipe models package.

All models for the recipe system, organized by functionality:
- base: RecipeCategory, RecipeTag
- recipe: Recipe
- ingredients: RecipeIngredient
- steps: RecipeStep
- interactions: UserRecipeInteraction, RecipeReview, CookingSession
"""

# Import all models to maintain compatibility
from .base import RecipeCategory, RecipeTag
from .recipe import Recipe
from .ingredients import RecipeIngredient
from .steps import RecipeStep
from .interactions import UserRecipeInteraction, RecipeReview, CookingSession

__all__ = [
    'RecipeCategory',
    'RecipeTag',
    'Recipe',
    'RecipeIngredient',
    'RecipeStep',
    'UserRecipeInteraction',
    'RecipeReview',
    'CookingSession',
]