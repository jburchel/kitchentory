from django.core.management.base import BaseCommand
from decimal import Decimal
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create initial subscription plans based on the pricing strategy'

    def handle(self, *args, **options):
        # Free Plan - Kitchen Starter
        free_plan, created = SubscriptionPlan.objects.get_or_create(
            tier='free',
            defaults={
                'name': 'Kitchen Starter',
                'description': 'Perfect for individuals trying the app, students, and minimal kitchen management needs.',
                'monthly_price': Decimal('0.00'),
                'yearly_price': Decimal('0.00'),
                
                # Limits
                'max_inventory_items': 50,
                'max_recipes_per_day': 5,
                'max_shopping_lists': 1,
                'max_household_members': 1,
                'max_saved_recipes': 3,
                
                # Features (all False for free)
                'has_recipe_matching': False,
                'has_advanced_matching': False,
                'has_meal_planning': False,
                'has_nutrition_tracking': False,
                'has_analytics': False,
                'has_advanced_analytics': False,
                'has_export': False,
                'has_api_access': False,
                'has_ocr_receipts': False,
                'has_voice_input': False,
                'has_priority_support': False,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Free plan: {free_plan}'))
        else:
            self.stdout.write(self.style.WARNING(f'Free plan already exists: {free_plan}'))

        # Premium Plan - Kitchen Pro
        premium_plan, created = SubscriptionPlan.objects.get_or_create(
            tier='premium',
            defaults={
                'name': 'Kitchen Pro',
                'description': 'Perfect for regular home cooks, couples, and small families who want advanced features.',
                'monthly_price': Decimal('4.99'),
                'yearly_price': Decimal('49.99'),  # 17% discount
                
                # Limits (None means unlimited)
                'max_inventory_items': None,
                'max_recipes_per_day': None,
                'max_shopping_lists': None,
                'max_household_members': 3,
                'max_saved_recipes': None,
                
                # Features
                'has_recipe_matching': True,
                'has_advanced_matching': True,
                'has_meal_planning': True,
                'has_nutrition_tracking': False,
                'has_analytics': True,
                'has_advanced_analytics': False,
                'has_export': True,
                'has_api_access': False,
                'has_ocr_receipts': False,
                'has_voice_input': False,
                'has_priority_support': False,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Premium plan: {premium_plan}'))
        else:
            self.stdout.write(self.style.WARNING(f'Premium plan already exists: {premium_plan}'))

        # Pro Plan - Kitchen Master
        pro_plan, created = SubscriptionPlan.objects.get_or_create(
            tier='pro',
            defaults={
                'name': 'Kitchen Master',
                'description': 'Perfect for food enthusiasts, large families, meal preppers, and health-conscious users.',
                'monthly_price': Decimal('9.99'),
                'yearly_price': Decimal('99.99'),  # 17% discount
                
                # Limits (None means unlimited)
                'max_inventory_items': None,
                'max_recipes_per_day': None,
                'max_shopping_lists': None,
                'max_household_members': 6,
                'max_saved_recipes': None,
                
                # Features (all True for pro)
                'has_recipe_matching': True,
                'has_advanced_matching': True,
                'has_meal_planning': True,
                'has_nutrition_tracking': True,
                'has_analytics': True,
                'has_advanced_analytics': True,
                'has_export': True,
                'has_api_access': True,
                'has_ocr_receipts': True,
                'has_voice_input': True,
                'has_priority_support': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Pro plan: {pro_plan}'))
        else:
            self.stdout.write(self.style.WARNING(f'Pro plan already exists: {pro_plan}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully processed all subscription plans!'
                f'\n- Free: ${free_plan.monthly_price}/month'
                f'\n- Premium: ${premium_plan.monthly_price}/month (${premium_plan.yearly_price}/year)'
                f'\n- Pro: ${pro_plan.monthly_price}/month (${pro_plan.yearly_price}/year)'
            )
        )