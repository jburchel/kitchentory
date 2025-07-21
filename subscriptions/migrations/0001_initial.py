# Generated manually to create subscription models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tier', models.CharField(choices=[('free', 'Free - Kitchen Starter'), ('premium', 'Premium - Kitchen Pro'), ('pro', 'Pro - Kitchen Master')], max_length=20, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('monthly_price', models.DecimalField(decimal_places=2, max_digits=6, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('yearly_price', models.DecimalField(decimal_places=2, max_digits=6, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('max_inventory_items', models.IntegerField(blank=True, help_text='None means unlimited', null=True)),
                ('max_recipes_per_day', models.IntegerField(blank=True, help_text='None means unlimited', null=True)),
                ('max_shopping_lists', models.IntegerField(blank=True, help_text='None means unlimited', null=True)),
                ('max_household_members', models.IntegerField(default=1)),
                ('max_saved_recipes', models.IntegerField(blank=True, help_text='None means unlimited', null=True)),
                ('has_recipe_matching', models.BooleanField(default=False)),
                ('has_advanced_matching', models.BooleanField(default=False)),
                ('has_meal_planning', models.BooleanField(default=False)),
                ('has_nutrition_tracking', models.BooleanField(default=False)),
                ('has_analytics', models.BooleanField(default=False)),
                ('has_advanced_analytics', models.BooleanField(default=False)),
                ('has_export', models.BooleanField(default=False)),
                ('has_api_access', models.BooleanField(default=False)),
                ('has_ocr_receipts', models.BooleanField(default=False)),
                ('has_voice_input', models.BooleanField(default=False)),
                ('has_priority_support', models.BooleanField(default=False)),
                ('stripe_product_id', models.CharField(blank=True, max_length=100)),
                ('stripe_monthly_price_id', models.CharField(blank=True, max_length=100)),
                ('stripe_yearly_price_id', models.CharField(blank=True, max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'subscription_plans',
                'ordering': ['monthly_price'],
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('active', 'Active'), ('canceled', 'Canceled'), ('past_due', 'Past Due'), ('trialing', 'Trialing'), ('paused', 'Paused'), ('expired', 'Expired')], default='active', max_length=20)),
                ('billing_period', models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=10)),
                ('stripe_customer_id', models.CharField(blank=True, max_length=100)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=100)),
                ('trial_start', models.DateTimeField(blank=True, null=True)),
                ('trial_end', models.DateTimeField(blank=True, null=True)),
                ('current_period_start', models.DateTimeField(default=django.utils.timezone.now)),
                ('current_period_end', models.DateTimeField()),
                ('canceled_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='subscriptions.subscriptionplan')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'subscriptions',
            },
        ),
        migrations.CreateModel(
            name='BillingHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('payment', 'Payment'), ('refund', 'Refund'), ('credit', 'Credit'), ('adjustment', 'Adjustment')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('succeeded', 'Succeeded'), ('failed', 'Failed'), ('refunded', 'Refunded')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('stripe_invoice_id', models.CharField(blank=True, max_length=100)),
                ('stripe_payment_intent_id', models.CharField(blank=True, max_length=100)),
                ('stripe_charge_id', models.CharField(blank=True, max_length=100)),
                ('description', models.TextField(blank=True)),
                ('invoice_url', models.URLField(blank=True)),
                ('invoice_pdf', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('subscription', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='billing_history', to='subscriptions.subscription')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='billing_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'billing_history',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='InventoryUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_count', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='inventory_usage', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'inventory_usage',
            },
        ),
        migrations.CreateModel(
            name='RecipeSearchUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('search_count', models.IntegerField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_search_usage', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'recipe_search_usage',
            },
        ),
        migrations.CreateModel(
            name='ShoppingListUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('list_count', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='shopping_list_usage', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'shopping_list_usage',
            },
        ),
        migrations.CreateModel(
            name='ExportUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('export_type', models.CharField(max_length=50)),
                ('export_format', models.CharField(max_length=20)),
                ('item_count', models.IntegerField(default=0)),
                ('file_size', models.IntegerField(default=0, help_text='Size in bytes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='export_usage', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'export_usage',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='recipesearchusage',
            unique_together={('user', 'date')},
        ),
    ]