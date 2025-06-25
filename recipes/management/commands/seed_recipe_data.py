from django.core.management.base import BaseCommand
from django.utils.text import slugify
from recipes.models import RecipeCategory, RecipeTag


class Command(BaseCommand):
    help = 'Seed recipe categories and tags'

    def handle(self, *args, **options):
        self.stdout.write('Seeding recipe categories and tags...')
        
        # Recipe Categories
        categories_data = [
            # Main Categories
            {'name': 'Italian', 'color': '#C8102E', 'order': 1},
            {'name': 'Mexican', 'color': '#006341', 'order': 2},
            {'name': 'Asian', 'color': '#FF6B35', 'order': 3},
            {'name': 'American', 'color': '#1F4E79', 'order': 4},
            {'name': 'Mediterranean', 'color': '#4285F4', 'order': 5},
            {'name': 'Indian', 'color': '#FF9933', 'order': 6},
            {'name': 'French', 'color': '#0055A4', 'order': 7},
            {'name': 'Thai', 'color': '#F4A460', 'order': 8},
            
            # Meal Types
            {'name': 'Breakfast', 'color': '#FFD700', 'order': 10},
            {'name': 'Lunch', 'color': '#32CD32', 'order': 11},
            {'name': 'Dinner', 'color': '#8B4513', 'order': 12},
            {'name': 'Snacks', 'color': '#FF69B4', 'order': 13},
            {'name': 'Desserts', 'color': '#DA70D6', 'order': 14},
            {'name': 'Beverages', 'color': '#00CED1', 'order': 15},
            
            # Cooking Methods
            {'name': 'Grilling', 'color': '#8B0000', 'order': 20},
            {'name': 'Baking', 'color': '#D2691E', 'order': 21},
            {'name': 'Slow Cooker', 'color': '#556B2F', 'order': 22},
            {'name': 'One Pot', 'color': '#4682B4', 'order': 23},
            {'name': 'No Cook', 'color': '#98FB98', 'order': 24},
        ]
        
        # Recipe Tags
        tags_data = [
            # Dietary
            {'name': 'Vegetarian', 'color': '#228B22'},
            {'name': 'Vegan', 'color': '#32CD32'},
            {'name': 'Gluten-Free', 'color': '#DAA520'},
            {'name': 'Dairy-Free', 'color': '#87CEEB'},
            {'name': 'Nut-Free', 'color': '#CD853F'},
            {'name': 'Low-Carb', 'color': '#FF6347'},
            {'name': 'Keto', 'color': '#9370DB'},
            {'name': 'Paleo', 'color': '#D2691E'},
            
            # Time & Effort
            {'name': 'Quick', 'color': '#FF4500'},  # Under 30 minutes
            {'name': 'Easy', 'color': '#7CFC00'},
            {'name': 'Make-Ahead', 'color': '#4169E1'},
            {'name': 'Freezer-Friendly', 'color': '#1E90FF'},
            {'name': 'Meal Prep', 'color': '#FF1493'},
            
            # Occasion
            {'name': 'Family-Friendly', 'color': '#FFA500'},
            {'name': 'Date Night', 'color': '#DC143C'},
            {'name': 'Party Food', 'color': '#FFD700'},
            {'name': 'Holiday', 'color': '#B22222'},
            {'name': 'Comfort Food', 'color': '#D2691E'},
            
            # Health
            {'name': 'Healthy', 'color': '#00FF7F'},
            {'name': 'Low-Calorie', 'color': '#98FB98'},
            {'name': 'High-Protein', 'color': '#FF6B6B'},
            {'name': 'Heart-Healthy', 'color': '#FF69B4'},
            
            # Budget
            {'name': 'Budget-Friendly', 'color': '#32CD32'},
            {'name': 'Expensive', 'color': '#8B0000'},
            
            # Season
            {'name': 'Summer', 'color': '#FFD700'},
            {'name': 'Fall', 'color': '#FF8C00'},
            {'name': 'Winter', 'color': '#4682B4'},
            {'name': 'Spring', 'color': '#98FB98'},
        ]
        
        # Create Categories
        created_categories = 0
        for cat_data in categories_data:
            category, created = RecipeCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'slug': slugify(cat_data['name']),
                    'color': cat_data['color'],
                    'order': cat_data['order']
                }
            )
            if created:
                created_categories += 1
                self.stdout.write(f"Created category: {category.name}")
        
        # Create Tags
        created_tags = 0
        for tag_data in tags_data:
            tag, created = RecipeTag.objects.get_or_create(
                name=tag_data['name'],
                defaults={
                    'slug': slugify(tag_data['name']),
                    'color': tag_data['color']
                }
            )
            if created:
                created_tags += 1
                self.stdout.write(f"Created tag: {tag.name}")
        
        # Create some subcategories
        subcategories_data = [
            {'name': 'Pasta', 'parent': 'Italian', 'color': '#C8102E'},
            {'name': 'Pizza', 'parent': 'Italian', 'color': '#C8102E'},
            {'name': 'Risotto', 'parent': 'Italian', 'color': '#C8102E'},
            
            {'name': 'Chinese', 'parent': 'Asian', 'color': '#FF6B35'},
            {'name': 'Japanese', 'parent': 'Asian', 'color': '#FF6B35'},
            {'name': 'Korean', 'parent': 'Asian', 'color': '#FF6B35'},
            
            {'name': 'Tacos', 'parent': 'Mexican', 'color': '#006341'},
            {'name': 'Burritos', 'parent': 'Mexican', 'color': '#006341'},
            
            {'name': 'Pancakes', 'parent': 'Breakfast', 'color': '#FFD700'},
            {'name': 'Smoothies', 'parent': 'Breakfast', 'color': '#FFD700'},
            {'name': 'Eggs', 'parent': 'Breakfast', 'color': '#FFD700'},
            
            {'name': 'Cakes', 'parent': 'Desserts', 'color': '#DA70D6'},
            {'name': 'Cookies', 'parent': 'Desserts', 'color': '#DA70D6'},
            {'name': 'Ice Cream', 'parent': 'Desserts', 'color': '#DA70D6'},
        ]
        
        created_subcategories = 0
        for subcat_data in subcategories_data:
            try:
                parent = RecipeCategory.objects.get(name=subcat_data['parent'])
                subcategory, created = RecipeCategory.objects.get_or_create(
                    name=subcat_data['name'],
                    parent=parent,
                    defaults={
                        'slug': slugify(subcat_data['name']),
                        'color': subcat_data['color'],
                        'order': 0
                    }
                )
                if created:
                    created_subcategories += 1
                    self.stdout.write(f"Created subcategory: {parent.name} > {subcategory.name}")
            except RecipeCategory.DoesNotExist:
                self.stdout.write(f"Parent category '{subcat_data['parent']}' not found for '{subcat_data['name']}'")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_categories} categories, '
                f'{created_subcategories} subcategories, and {created_tags} tags'
            )
        )