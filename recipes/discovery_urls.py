from django.urls import path
from . import discovery_views

app_name = "discovery"

urlpatterns = [
    # Discovery dashboard
    path("", discovery_views.discovery_dashboard, name="dashboard"),
    # Recipe matching endpoints
    path("matches/", discovery_views.recipe_matches, name="matches"),
    path("check/<slug:slug>/", discovery_views.check_recipe_match, name="check_match"),
    # Almost there recipes
    path("almost-there/", discovery_views.almost_there_recipes, name="almost_there"),
    # Shopping list integration
    path(
        "add-missing/", discovery_views.add_missing_to_shopping_list, name="add_missing"
    ),
    # Substitutions
    path(
        "substitutions/", discovery_views.ingredient_substitutions, name="substitutions"
    ),
]
