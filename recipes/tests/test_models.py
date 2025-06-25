"""
Unit tests for recipe models.
"""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from recipes.models import (
    RecipeCategory, Recipe, RecipeIngredient, RecipeStep,
    RecipeTag, UserRecipeInteraction, RecipeReview
)
from inventory.models import Category, Product
from accounts.models import Household

User = get_user_model()


class RecipeCategoryModelTest(TestCase):
    """Test cases for RecipeCategory model."""
    
    def setUp(self):
        self.category = RecipeCategory.objects.create(
            name="Main Course",
            description="Main course recipes"
        )
    
    def test_recipe_category_creation(self):
        """Test basic recipe category creation."""
        self.assertEqual(self.category.name, "Main Course")
        self.assertEqual(self.category.description, "Main course recipes")
        self.assertEqual(str(self.category), "Main Course")
    
    def test_recipe_category_slug_generation(self):
        """Test automatic slug generation."""
        category = RecipeCategory.objects.create(name="Quick & Easy Meals")
        self.assertEqual(category.slug, "quick-easy-meals")
    
    def test_recipe_category_unique_name(self):
        """Test that category names must be unique."""
        with self.assertRaises(IntegrityError):
            RecipeCategory.objects.create(name="Main Course")


class RecipeModelTest(TestCase):
    """Test cases for Recipe model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testchef",
            email="chef@example.com",
            password="testpass123"
        )
        self.category = RecipeCategory.objects.create(name="Main Course")
        self.recipe = Recipe.objects.create(
            name="Test Recipe",
            description="A delicious test recipe",
            category=self.category,
            created_by=self.user,
            servings=4,
            prep_time=15,
            cook_time=30,
            instructions="Mix and cook",
            difficulty="medium"
        )
    
    def test_recipe_creation(self):
        """Test basic recipe creation."""
        self.assertEqual(self.recipe.name, "Test Recipe")
        self.assertEqual(self.recipe.category, self.category)
        self.assertEqual(self.recipe.created_by, self.user)
        self.assertEqual(self.recipe.servings, 4)
        self.assertEqual(self.recipe.prep_time, 15)
        self.assertEqual(self.recipe.cook_time, 30)
        self.assertEqual(str(self.recipe), "Test Recipe")
    
    def test_recipe_slug_generation(self):
        """Test automatic slug generation."""
        recipe = Recipe.objects.create(
            name="Amazing Pasta Recipe!",
            category=self.category,
            created_by=self.user
        )
        self.assertEqual(recipe.slug, "amazing-pasta-recipe")
    
    def test_recipe_total_time_property(self):
        """Test total_time property calculation."""
        expected_total = self.recipe.prep_time + self.recipe.cook_time
        self.assertEqual(self.recipe.total_time, expected_total)
    
    def test_recipe_validation(self):
        """Test recipe field validation."""
        # Test negative servings
        self.recipe.servings = -1
        with self.assertRaises(ValidationError):
            self.recipe.full_clean()
        
        # Test negative prep time
        self.recipe.servings = 4  # Reset
        self.recipe.prep_time = -5
        with self.assertRaises(ValidationError):
            self.recipe.full_clean()
    
    def test_recipe_is_public_default(self):
        """Test that recipes are private by default."""
        self.assertFalse(self.recipe.is_public)
    
    def test_recipe_average_rating_calculation(self):
        """Test average rating calculation."""
        # Initially no rating
        self.assertIsNone(self.recipe.average_rating)
        
        # This would be calculated from reviews
        self.recipe.average_rating = Decimal('4.5')
        self.recipe.save()
        self.assertEqual(self.recipe.average_rating, Decimal('4.5'))


class RecipeIngredientModelTest(TestCase):
    """Test cases for RecipeIngredient model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testchef",
            email="chef@example.com",
            password="testpass123"
        )
        self.recipe_category = RecipeCategory.objects.create(name="Main Course")
        self.recipe = Recipe.objects.create(
            name="Test Recipe",
            category=self.recipe_category,
            created_by=self.user
        )
        self.product_category = Category.objects.create(name="Vegetables")
        self.product = Product.objects.create(
            name="Tomato",
            category=self.product_category
        )
        self.ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            product=self.product,
            quantity=Decimal('2.0'),
            unit="pieces",
            preparation="diced",
            order=1
        )
    
    def test_recipe_ingredient_creation(self):
        """Test basic recipe ingredient creation."""
        self.assertEqual(self.ingredient.recipe, self.recipe)
        self.assertEqual(self.ingredient.product, self.product)
        self.assertEqual(self.ingredient.quantity, Decimal('2.0'))
        self.assertEqual(self.ingredient.unit, "pieces")
        self.assertEqual(self.ingredient.preparation, "diced")
        expected_str = "2.0 pieces Tomato (diced)"
        self.assertEqual(str(self.ingredient), expected_str)
    
    def test_recipe_ingredient_without_preparation(self):
        """Test recipe ingredient without preparation method."""
        ingredient = RecipeIngredient.objects.create(
            recipe=self.recipe,
            product=self.product,
            quantity=Decimal('1.0'),
            unit="cup",
            order=2
        )
        expected_str = "1.0 cup Tomato"
        self.assertEqual(str(ingredient), expected_str)
    
    def test_recipe_ingredient_validation(self):
        """Test recipe ingredient validation."""
        # Test negative quantity
        self.ingredient.quantity = Decimal('-1.0')
        with self.assertRaises(ValidationError):
            self.ingredient.full_clean()
    
    def test_recipe_ingredient_ordering(self):
        """Test recipe ingredient ordering."""
        ingredient2 = RecipeIngredient.objects.create(
            recipe=self.recipe,
            product=self.product,
            quantity=Decimal('1.0'),
            unit="cup",
            order=2
        )
        
        ingredients = self.recipe.ingredients.all()
        self.assertEqual(ingredients[0], self.ingredient)  # order=1 by default
        self.assertEqual(ingredients[1], ingredient2)     # order=2


class RecipeStepModelTest(TestCase):
    """Test cases for RecipeStep model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testchef",
            email="chef@example.com",
            password="testpass123"
        )
        self.category = RecipeCategory.objects.create(name="Main Course")
        self.recipe = Recipe.objects.create(
            name="Test Recipe",
            category=self.category,
            created_by=self.user
        )
        self.step = RecipeStep.objects.create(
            recipe=self.recipe,
            step_number=1,
            instruction="Heat oil in a pan",
            time_minutes=5
        )
    
    def test_recipe_step_creation(self):
        """Test basic recipe step creation."""
        self.assertEqual(self.step.recipe, self.recipe)
        self.assertEqual(self.step.step_number, 1)
        self.assertEqual(self.step.instruction, "Heat oil in a pan")
        self.assertEqual(self.step.time_minutes, 5)
        expected_str = "Step 1: Heat oil in a pan"
        self.assertEqual(str(self.step), expected_str)
    
    def test_recipe_step_ordering(self):
        """Test recipe step ordering."""
        step2 = RecipeStep.objects.create(
            recipe=self.recipe,
            step_number=2,
            instruction="Add ingredients"
        )
        
        steps = self.recipe.steps.all()
        self.assertEqual(steps[0], self.step)
        self.assertEqual(steps[1], step2)
    
    def test_recipe_step_validation(self):
        """Test recipe step validation."""
        # Test negative step number
        self.step.step_number = -1
        with self.assertRaises(ValidationError):
            self.step.full_clean()
        
        # Test negative duration
        self.step.step_number = 1  # Reset
        self.step.time_minutes = -5
        with self.assertRaises(ValidationError):
            self.step.full_clean()


class RecipeTagModelTest(TestCase):
    """Test cases for RecipeTag model."""
    
    def setUp(self):
        self.tag = RecipeTag.objects.create(
            name="vegetarian",
            description="Suitable for vegetarians"
        )
    
    def test_recipe_tag_creation(self):
        """Test basic recipe tag creation."""
        self.assertEqual(self.tag.name, "vegetarian")
        self.assertEqual(self.tag.description, "Suitable for vegetarians")
        self.assertEqual(str(self.tag), "vegetarian")
    
    def test_recipe_tag_unique_name(self):
        """Test that tag names must be unique."""
        with self.assertRaises(IntegrityError):
            RecipeTag.objects.create(name="vegetarian")
    
    def test_recipe_tag_lowercase_name(self):
        """Test that tag names are stored in lowercase."""
        tag = RecipeTag.objects.create(name="VEGAN")
        self.assertEqual(tag.name, "vegan")


class UserRecipeInteractionModelTest(TestCase):
    """Test cases for UserRecipeInteraction model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="user@example.com",
            password="testpass123"
        )
        self.chef = User.objects.create_user(
            username="testchef",
            email="chef@example.com",
            password="testpass123"
        )
        self.category = RecipeCategory.objects.create(name="Main Course")
        self.recipe = Recipe.objects.create(
            name="Test Recipe",
            category=self.category,
            created_by=self.chef
        )
        self.interaction = UserRecipeInteraction.objects.create(
            user=self.user,
            recipe=self.recipe,
            interaction_type='rate',
            rating=4,
            is_favorite=True
        )
    
    def test_user_recipe_interaction_creation(self):
        """Test basic interaction creation."""
        self.assertEqual(self.interaction.user, self.user)
        self.assertEqual(self.interaction.recipe, self.recipe)
        self.assertEqual(self.interaction.rating, 4)
        self.assertTrue(self.interaction.is_favorite)
        self.assertEqual(self.interaction.times_cooked, 0)
    
    def test_user_recipe_interaction_unique_constraint(self):
        """Test that user-recipe combinations must be unique."""
        with self.assertRaises(IntegrityError):
            UserRecipeInteraction.objects.create(
                user=self.user,
                recipe=self.recipe,
                interaction_type='rate',
                rating=3
            )
    
    def test_rating_validation(self):
        """Test rating validation."""
        # Test rating too low
        self.interaction.rating = 0
        with self.assertRaises(ValidationError):
            self.interaction.full_clean()
        
        # Test rating too high
        self.interaction.rating = 6
        with self.assertRaises(ValidationError):
            self.interaction.full_clean()
        
        # Test valid rating
        self.interaction.rating = 3
        self.interaction.full_clean()  # Should not raise
    
    def test_increment_cooked_count(self):
        """Test incrementing times cooked."""
        initial_count = self.interaction.times_cooked
        self.interaction.increment_cooked_count()
        self.assertEqual(self.interaction.times_cooked, initial_count + 1)


class RecipeReviewModelTest(TestCase):
    """Test cases for RecipeReview model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="reviewer",
            email="reviewer@example.com",
            password="testpass123"
        )
        self.chef = User.objects.create_user(
            username="testchef",
            email="chef@example.com",
            password="testpass123"
        )
        self.category = RecipeCategory.objects.create(name="Main Course")
        self.recipe = Recipe.objects.create(
            name="Test Recipe",
            category=self.category,
            created_by=self.chef
        )
        self.review = RecipeReview.objects.create(
            recipe=self.recipe,
            user=self.user,
            rating=5,
            comment="Absolutely delicious!",
            would_make_again=True
        )
    
    def test_recipe_review_creation(self):
        """Test basic review creation."""
        self.assertEqual(self.review.recipe, self.recipe)
        self.assertEqual(self.review.user, self.user)
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.comment, "Absolutely delicious!")
        self.assertTrue(self.review.would_make_again)
        expected_str = f"Review by {self.user.username} for {self.recipe.name}"
        self.assertEqual(str(self.review), expected_str)
    
    def test_review_rating_validation(self):
        """Test review rating validation."""
        # Test rating too low
        self.review.rating = 0
        with self.assertRaises(ValidationError):
            self.review.full_clean()
        
        # Test rating too high
        self.review.rating = 6
        with self.assertRaises(ValidationError):
            self.review.full_clean()
    
    def test_review_unique_constraint(self):
        """Test that users can only review a recipe once."""
        with self.assertRaises(IntegrityError):
            RecipeReview.objects.create(
                recipe=self.recipe,
                user=self.user,
                rating=3,
                comment="Different review"
            )


@pytest.mark.django_db
class RecipeQuerySetTest:
    """Test cases for Recipe QuerySet methods."""
    
    def setup_method(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testchef",
            email="chef@example.com",
            password="testpass123"
        )
        self.category = RecipeCategory.objects.create(name="Main Course")
        
        # Create public recipe
        self.public_recipe = Recipe.objects.create(
            name="Public Recipe",
            category=self.category,
            created_by=self.user,
            is_public=True,
            average_rating=Decimal('4.5')
        )
        
        # Create private recipe
        self.private_recipe = Recipe.objects.create(
            name="Private Recipe",
            category=self.category,
            created_by=self.user,
            is_public=False,
            average_rating=Decimal('3.0')
        )
    
    def test_public_queryset_method(self):
        """Test public() queryset method."""
        public_recipes = Recipe.objects.public()
        assert self.public_recipe in public_recipes
        assert self.private_recipe not in public_recipes
    
    def test_by_category_queryset_method(self):
        """Test by_category() queryset method."""
        recipes_in_category = Recipe.objects.by_category(self.category)
        assert self.public_recipe in recipes_in_category
        assert self.private_recipe in recipes_in_category
        
        # Test with different category
        other_category = RecipeCategory.objects.create(name="Dessert")
        recipes_in_other = Recipe.objects.by_category(other_category)
        assert self.public_recipe not in recipes_in_other
        assert self.private_recipe not in recipes_in_other
    
    def test_highly_rated_queryset_method(self):
        """Test highly_rated() queryset method."""
        highly_rated = Recipe.objects.highly_rated(min_rating=4.0)
        assert self.public_recipe in highly_rated
        assert self.private_recipe not in highly_rated
    
    def test_for_ingredients_queryset_method(self):
        """Test for_ingredients() queryset method."""
        # Create products and ingredients
        product_category = Category.objects.create(name="Vegetables")
        tomato = Product.objects.create(name="Tomato", category=product_category)
        onion = Product.objects.create(name="Onion", category=product_category)
        
        # Add ingredients to public recipe
        RecipeIngredient.objects.create(
            recipe=self.public_recipe,
            product=tomato,
            quantity=Decimal('2.0'),
            unit="pieces"
        )
        RecipeIngredient.objects.create(
            recipe=self.public_recipe,
            product=onion,
            quantity=Decimal('1.0'),
            unit="pieces"
        )
        
        # Test with available ingredients
        available_products = [tomato, onion]
        matching_recipes = Recipe.objects.for_ingredients(available_products)
        assert self.public_recipe in matching_recipes
        assert self.private_recipe not in matching_recipes