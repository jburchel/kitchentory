"""
Django management command to create comprehensive sample data for Kitchentory.
This ensures database compatibility between SQLite3 (dev) and PostgreSQL (production).
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random

from accounts.models import Household
from inventory.models import Category, Product, InventoryItem, StorageLocation
from recipes.models import Recipe, RecipeIngredient, RecipeStep
from shopping.models import Store, ShoppingList, ShoppingListItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Create comprehensive sample data for testing Kitchentory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating sample data',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of sample users to create (default: 5)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self.clear_data()

        self.stdout.write('Creating sample data...')
        
        # Create in order due to dependencies
        categories = self.create_categories()
        stores = self.create_stores()
        households, users = self.create_households_and_users(options['users'])
        storage_locations = self.create_storage_locations(households)
        products = self.create_products(categories)
        inventory_items = self.create_inventory_items(households, products, storage_locations)
        recipes = self.create_recipes(products, users)
        shopping_lists = self.create_shopping_lists(households, users, stores, products)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data:\n'
                f'  - {len(categories)} categories\n'
                f'  - {len(storage_locations)} storage locations\n' 
                f'  - {len(stores)} stores\n'
                f'  - {len(households)} households\n'
                f'  - {len(users)} users\n'
                f'  - {len(products)} products\n'
                f'  - {len(inventory_items)} inventory items\n'
                f'  - {len(recipes)} recipes\n'
                f'  - {len(shopping_lists)} shopping lists'
            )
        )

    def clear_data(self):
        """Clear existing data (except superusers)"""
        ShoppingListItem.objects.all().delete()
        ShoppingList.objects.all().delete()
        RecipeStep.objects.all().delete()
        RecipeIngredient.objects.all().delete()
        Recipe.objects.all().delete()
        InventoryItem.objects.all().delete()
        Product.objects.all().delete()
        Store.objects.all().delete()
        StorageLocation.objects.all().delete()
        Category.objects.all().delete()
        
        # Keep superusers, delete other users and households
        User.objects.filter(is_superuser=False).delete()
        Household.objects.all().delete()

    def create_categories(self):
        """Create food categories"""
        categories_data = [
            ('Fruits', None),
            ('Vegetables', None),
            ('Dairy', None),
            ('Meat & Seafood', None),
            ('Pantry', None),
            ('Beverages', None),
            ('Frozen', None),
            ('Bakery', None),
            ('Snacks', None),
            ('Condiments', None),
            # Subcategories
            ('Citrus', 'Fruits'),
            ('Berries', 'Fruits'),
            ('Leafy Greens', 'Vegetables'),
            ('Root Vegetables', 'Vegetables'),
            ('Milk Products', 'Dairy'),
            ('Cheese', 'Dairy'),
            ('Fresh Meat', 'Meat & Seafood'),
            ('Fish', 'Meat & Seafood'),
            ('Grains', 'Pantry'),
            ('Spices', 'Pantry'),
        ]

        categories = {}
        for name, parent_name in categories_data:
            parent = categories.get(parent_name) if parent_name else None
            category = Category.objects.create(
                name=name,
                parent=parent,
                description=f'{name} category for kitchen inventory'
            )
            categories[name] = category

        return list(categories.values())

    def create_storage_locations(self, households):
        """Create storage locations for each household"""
        locations_data = [
            ('Refrigerator', 'refrigerator'),
            ('Freezer', 'freezer'),
            ('Pantry', 'pantry'),
            ('Counter', 'counter'),
            ('Fruit Bowl', 'counter'),
            ('Spice Rack', 'cabinet'),
            ('Wine Rack', 'other'),
            ('Garage Fridge', 'refrigerator'),
        ]

        locations = []
        for household in households:
            for name, location_type in locations_data:
                location = StorageLocation.objects.create(
                    household=household,
                    name=name,
                    location_type=location_type,
                    notes=f'{name} in {household.name}'
                )
                locations.append(location)

        return locations

    def create_stores(self):
        """Create sample stores"""
        stores_data = [
            {
                'name': 'Whole Foods Market',
                'store_type': 'grocery',
                'is_chain': True,
                'chain_name': 'Whole Foods',
                'sections': ['Produce', 'Dairy', 'Meat & Seafood', 'Bakery', 'Pantry', 'Frozen', 'Beverages']
            },
            {
                'name': 'Safeway',
                'store_type': 'supermarket',
                'is_chain': True,
                'chain_name': 'Safeway',
                'sections': ['Produce', 'Dairy', 'Meat', 'Bakery', 'Canned Goods', 'Frozen', 'Beverages', 'Pharmacy']
            },
            {
                'name': 'Trader Joe\'s',
                'store_type': 'grocery',
                'is_chain': True,
                'chain_name': 'Trader Joe\'s',
                'sections': ['Produce', 'Dairy', 'Meat', 'Frozen', 'Pantry', 'Snacks', 'Wine']
            },
            {
                'name': 'Local Market',
                'store_type': 'grocery',
                'is_chain': False,
                'sections': ['Produce', 'Dairy', 'Meat', 'Bakery', 'Pantry']
            }
        ]

        stores = []
        for store_data in stores_data:
            store = Store.objects.create(**store_data)
            stores.append(store)

        return stores

    def create_households_and_users(self, num_users):
        """Create sample households and users"""
        households_data = [
            {'name': 'The Johnson Family', 'timezone': 'America/New_York', 'currency': 'USD'},
            {'name': 'Miller Household', 'timezone': 'America/Los_Angeles', 'currency': 'USD'},
            {'name': 'The Smiths', 'timezone': 'America/Chicago', 'currency': 'USD'},
        ]

        users_data = [
            {'username': 'sarah_j', 'email': 'sarah@kitchentory.test', 'first_name': 'Sarah', 'last_name': 'Johnson'},
            {'username': 'mike_j', 'email': 'mike@kitchentory.test', 'first_name': 'Mike', 'last_name': 'Johnson'}, 
            {'username': 'emma_m', 'email': 'emma@kitchentory.test', 'first_name': 'Emma', 'last_name': 'Miller'},
            {'username': 'david_m', 'email': 'david@kitchentory.test', 'first_name': 'David', 'last_name': 'Miller'},
            {'username': 'lisa_s', 'email': 'lisa@kitchentory.test', 'first_name': 'Lisa', 'last_name': 'Smith'},
        ]

        households = []
        for household_data in households_data:
            household = Household.objects.create(**household_data)
            households.append(household)

        users = []
        for i, user_data in enumerate(users_data[:num_users]):
            user = User.objects.create_user(
                password='kitchentory123',
                **user_data
            )
            # Assign to household (multiple users per household)
            household_index = i // 2  # 2 users per household roughly
            if household_index < len(households):
                user.household = households[household_index]
                user.save()
            users.append(user)

        return households, users

    def create_products(self, categories):
        """Create sample products"""
        products_data = [
            # Fruits
            ('Bananas', 'Fruits', 'Fresh yellow bananas', '4011'),
            ('Apples - Gala', 'Fruits', 'Fresh Gala apples', '4133'),
            ('Oranges', 'Citrus', 'Fresh navel oranges', '4012'),
            ('Strawberries', 'Berries', 'Fresh strawberries', '4108'),
            ('Blueberries', 'Berries', 'Fresh blueberries', '4109'),
            
            # Vegetables  
            ('Spinach', 'Leafy Greens', 'Fresh baby spinach', '4090'),
            ('Carrots', 'Root Vegetables', 'Fresh carrots', '4094'),
            ('Broccoli', 'Vegetables', 'Fresh broccoli crowns', '4060'),
            ('Onions - Yellow', 'Root Vegetables', 'Yellow cooking onions', '4093'),
            ('Bell Peppers', 'Vegetables', 'Red bell peppers', '4088'),
            
            # Dairy
            ('Whole Milk', 'Milk Products', 'Organic whole milk', '2100001'),
            ('Cheddar Cheese', 'Cheese', 'Sharp cheddar cheese block', '2100002'),
            ('Greek Yogurt', 'Dairy', 'Plain Greek yogurt', '2100003'),
            ('Butter', 'Dairy', 'Unsalted butter', '2100004'),
            ('Eggs', 'Dairy', 'Large brown eggs', '2100005'),
            
            # Meat & Seafood
            ('Chicken Breast', 'Fresh Meat', 'Boneless skinless chicken breast', '3100001'),
            ('Ground Beef', 'Fresh Meat', '85% lean ground beef', '3100002'),
            ('Salmon Fillet', 'Fish', 'Fresh Atlantic salmon', '3100003'),
            
            # Pantry
            ('Brown Rice', 'Grains', 'Long grain brown rice', '5100001'),
            ('Pasta - Spaghetti', 'Grains', 'Whole wheat spaghetti', '5100002'),
            ('Olive Oil', 'Condiments', 'Extra virgin olive oil', '5100003'),
            ('Salt', 'Spices', 'Sea salt', '5100004'),
            ('Black Pepper', 'Spices', 'Ground black pepper', '5100005'),
            
            # Beverages
            ('Orange Juice', 'Beverages', 'Fresh squeezed orange juice', '6100001'),
            ('Coffee Beans', 'Beverages', 'Arabica coffee beans', '6100002'),
        ]

        category_map = {cat.name: cat for cat in categories}
        products = []

        for name, category_name, description, barcode in products_data:
            category = category_map.get(category_name)
            product = Product.objects.create(
                name=name,
                description=description,
                barcode=barcode,
                category=category,
                brand='Sample Brand',
                default_unit='count'
            )
            products.append(product)

        return products

    def create_inventory_items(self, households, products, storage_locations):
        """Create sample inventory items"""
        inventory_items = []
        
        for household in households:
            # Get users and storage locations for this household
            household_users = [user for user in User.objects.filter(household=household)]
            if not household_users:
                continue
                
            household_locations = [loc for loc in storage_locations if loc.household == household]
            
            # Create 10-20 random inventory items per household
            num_items = random.randint(10, 20)
            selected_products = random.sample(products, min(num_items, len(products)))
            
            for product in selected_products:
                # Random quantity and expiration
                quantity = Decimal(str(random.uniform(0.5, 5.0)))
                days_until_expiry = random.randint(1, 30)
                expiration_date = timezone.now().date() + timedelta(days=days_until_expiry)
                
                # Choose appropriate storage location based on product category
                if product.category and product.category.name in ['Dairy', 'Meat & Seafood']:
                    location = next((loc for loc in household_locations if loc.name == 'Refrigerator'), household_locations[0])
                elif product.category and product.category.name == 'Frozen':
                    location = next((loc for loc in household_locations if loc.name == 'Freezer'), household_locations[0])
                elif product.category and product.category.name == 'Fruits':
                    location = next((loc for loc in household_locations if loc.name == 'Fruit Bowl'), household_locations[0])
                else:
                    location = next((loc for loc in household_locations if loc.name == 'Pantry'), household_locations[0])

                inventory_item = InventoryItem.objects.create(
                    product=product,
                    user=random.choice(household_users),
                    household=household,
                    current_quantity=quantity,
                    unit=product.default_unit or 'count',
                    location=location,
                    expiration_date=expiration_date,
                    purchase_date=timezone.now().date() - timedelta(days=random.randint(0, 7))
                )
                inventory_items.append(inventory_item)

        return inventory_items

    def create_recipes(self, products, users):
        """Create sample recipes"""
        recipes_data = [
            {
                'title': 'Spaghetti Carbonara',
                'description': 'Classic Italian pasta dish with eggs, cheese, and pancetta',
                'prep_time': 15,
                'cook_time': 20,
                'servings': 4,
                'difficulty': 'medium',
                'ingredients': [
                    ('Pasta - Spaghetti', '1', 'lb'),
                    ('Eggs', '3', 'count'),
                    ('Cheddar Cheese', '1', 'cup'),
                    ('Black Pepper', '1', 'tsp'),
                ],
                'steps': [
                    'Bring a large pot of salted water to boil',
                    'Cook spaghetti according to package directions',
                    'Beat eggs with cheese and pepper in a bowl',
                    'Drain pasta and toss with egg mixture',
                    'Serve immediately with extra cheese'
                ]
            },
            {
                'title': 'Grilled Chicken & Vegetables',
                'description': 'Healthy grilled chicken with seasonal vegetables',
                'prep_time': 20,
                'cook_time': 25,
                'servings': 4,
                'difficulty': 'easy',
                'ingredients': [
                    ('Chicken Breast', '4', 'count'),
                    ('Bell Peppers', '2', 'count'),
                    ('Broccoli', '1', 'head'),
                    ('Olive Oil', '2', 'tbsp'),
                    ('Salt', '1', 'tsp'),
                ],
                'steps': [
                    'Preheat grill to medium-high heat',
                    'Season chicken with salt and pepper',
                    'Cut vegetables into uniform pieces',
                    'Grill chicken 6-7 minutes per side',
                    'Grill vegetables until tender',
                    'Serve hot'
                ]
            },
            {
                'title': 'Berry Smoothie Bowl',
                'description': 'Nutritious breakfast bowl with fresh berries',
                'prep_time': 10,
                'cook_time': 0,
                'servings': 2,
                'difficulty': 'easy',
                'ingredients': [
                    ('Strawberries', '1', 'cup'),
                    ('Blueberries', '0.5', 'cup'),
                    ('Greek Yogurt', '1', 'cup'),
                    ('Bananas', '1', 'count'),
                ],
                'steps': [
                    'Blend yogurt and banana until smooth',
                    'Pour into bowl',
                    'Top with fresh berries',
                    'Serve immediately'
                ]
            }
        ]

        product_map = {product.name: product for product in products}
        recipes = []

        for recipe_data in recipes_data:
            # Get a random user as recipe creator
            creator = random.choice(users) if users else None
            if not creator:
                continue
                
            recipe = Recipe.objects.create(
                title=recipe_data['title'],
                description=recipe_data['description'],
                prep_time=recipe_data['prep_time'],
                cook_time=recipe_data['cook_time'],
                servings=recipe_data['servings'],
                difficulty=recipe_data['difficulty'],
                created_by=creator,
                instructions='\n'.join(recipe_data['steps'])
            )

            # Add ingredients
            for order, (ingredient_name, amount, unit) in enumerate(recipe_data['ingredients'], 1):
                product = product_map.get(ingredient_name)
                if product:
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        product=product,
                        name=ingredient_name,
                        quantity=Decimal(amount) if amount.replace('.', '').isdigit() else Decimal('1'),
                        unit=unit,
                        order=order,
                        notes=f'{amount} {unit}'
                    )

            # Add steps
            for i, step in enumerate(recipe_data['steps'], 1):
                RecipeStep.objects.create(
                    recipe=recipe,
                    step_number=i,
                    instruction=step
                )

            recipes.append(recipe)

        return recipes

    def create_shopping_lists(self, households, users, stores, products):
        """Create sample shopping lists"""
        shopping_lists = []

        for household in households:
            household_users = [user for user in users if user.household == household]
            if not household_users:
                continue

            # Create 2-3 shopping lists per household
            for i in range(random.randint(2, 3)):
                creator = random.choice(household_users)
                store = random.choice(stores)
                
                list_names = [
                    'Weekly Groceries',
                    'Party Supplies',
                    'Thanksgiving Shopping',
                    'Quick Run',
                    'Bulk Shopping'
                ]
                
                shopping_list = ShoppingList.objects.create(
                    name=f'{random.choice(list_names)} - {household.name}',
                    description=f'Shopping list for {household.name}',
                    created_by=creator,
                    household=household,
                    store=store,
                    status=random.choice(['active', 'shopping', 'completed']),
                    generation_source='manual'
                )

                # Add 5-15 items to each list
                num_items = random.randint(5, 15)
                selected_products = random.sample(products, min(num_items, len(products)))

                for product in selected_products:
                    quantity = Decimal(str(random.uniform(1, 5)))
                    estimated_price = Decimal(str(random.uniform(1.50, 25.00)))
                    
                    ShoppingListItem.objects.create(
                        shopping_list=shopping_list,
                        product=product,
                        name=product.name,
                        quantity=quantity,
                        unit=product.default_unit or 'count',
                        estimated_price=estimated_price,
                        category=product.category.name if product.category else 'Other',
                        is_purchased=random.choice([True, False]) if shopping_list.status == 'completed' else False,
                        priority=random.choice(['normal', 'normal', 'high', 'low']),  # mostly normal
                        added_by=creator
                    )

                shopping_lists.append(shopping_list)

        return shopping_lists