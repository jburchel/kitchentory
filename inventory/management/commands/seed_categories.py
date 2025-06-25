from django.core.management.base import BaseCommand
from django.utils.text import slugify
from inventory.models import Category


class Command(BaseCommand):
    help = 'Seeds initial product categories'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Produce',
                'slug': 'produce',
                'order': 1,
                'children': [
                    {'name': 'Fruits', 'slug': 'fruits'},
                    {'name': 'Vegetables', 'slug': 'vegetables'},
                    {'name': 'Herbs', 'slug': 'herbs'},
                ]
            },
            {
                'name': 'Dairy & Eggs',
                'slug': 'dairy',
                'order': 2,
                'children': [
                    {'name': 'Milk', 'slug': 'milk'},
                    {'name': 'Cheese', 'slug': 'cheese'},
                    {'name': 'Yogurt', 'slug': 'yogurt'},
                    {'name': 'Eggs', 'slug': 'eggs'},
                ]
            },
            {
                'name': 'Meat & Seafood',
                'slug': 'meat',
                'order': 3,
                'children': [
                    {'name': 'Beef', 'slug': 'beef'},
                    {'name': 'Pork', 'slug': 'pork'},
                    {'name': 'Poultry', 'slug': 'poultry'},
                    {'name': 'Fish', 'slug': 'fish'},
                    {'name': 'Seafood', 'slug': 'seafood'},
                ]
            },
            {
                'name': 'Pantry',
                'slug': 'pantry',
                'order': 4,
                'children': [
                    {'name': 'Grains & Pasta', 'slug': 'grains-pasta'},
                    {'name': 'Canned Goods', 'slug': 'canned-goods'},
                    {'name': 'Condiments', 'slug': 'condiments'},
                    {'name': 'Oils & Vinegars', 'slug': 'oils-vinegars'},
                    {'name': 'Spices', 'slug': 'spices'},
                    {'name': 'Baking', 'slug': 'baking'},
                ]
            },
            {
                'name': 'Frozen',
                'slug': 'frozen',
                'order': 5,
                'children': [
                    {'name': 'Frozen Vegetables', 'slug': 'frozen-vegetables'},
                    {'name': 'Frozen Fruits', 'slug': 'frozen-fruits'},
                    {'name': 'Frozen Meals', 'slug': 'frozen-meals'},
                    {'name': 'Ice Cream', 'slug': 'ice-cream'},
                ]
            },
            {
                'name': 'Beverages',
                'slug': 'beverages',
                'order': 6,
                'children': [
                    {'name': 'Water', 'slug': 'water'},
                    {'name': 'Juices', 'slug': 'juices'},
                    {'name': 'Soft Drinks', 'slug': 'soft-drinks'},
                    {'name': 'Coffee & Tea', 'slug': 'coffee-tea'},
                    {'name': 'Alcoholic', 'slug': 'alcoholic'},
                ]
            },
            {
                'name': 'Snacks',
                'slug': 'snacks',
                'order': 7,
                'children': [
                    {'name': 'Chips', 'slug': 'chips'},
                    {'name': 'Cookies', 'slug': 'cookies'},
                    {'name': 'Candy', 'slug': 'candy'},
                    {'name': 'Nuts', 'slug': 'nuts'},
                ]
            },
            {
                'name': 'Other',
                'slug': 'other',
                'order': 8,
                'children': []
            }
        ]
        
        created_count = 0
        
        for parent_data in categories:
            children = parent_data.pop('children', [])
            
            parent, created = Category.objects.get_or_create(
                slug=parent_data['slug'],
                defaults=parent_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created parent category: {parent.name}')
                )
            
            for child_data in children:
                child_data['parent'] = parent
                child, created = Category.objects.get_or_create(
                    slug=child_data['slug'],
                    defaults=child_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  Created child category: {child.name}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal categories created: {created_count}')
        )