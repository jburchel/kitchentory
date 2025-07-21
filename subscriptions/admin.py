from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    SubscriptionPlan, Subscription, BillingHistory,
    InventoryUsage, RecipeSearchUsage, ShoppingListUsage, ExportUsage
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'tier', 'name', 'monthly_price', 'yearly_price', 
        'max_inventory_items', 'max_recipes_per_day', 'is_active'
    ]
    list_filter = ['tier', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tier', 'name', 'description', 'is_active')
        }),
        ('Pricing', {
            'fields': ('monthly_price', 'yearly_price')
        }),
        ('Feature Limits', {
            'fields': (
                'max_inventory_items', 'max_recipes_per_day', 
                'max_shopping_lists', 'max_household_members',
                'max_saved_recipes'
            )
        }),
        ('Feature Flags', {
            'fields': (
                'has_recipe_matching', 'has_advanced_matching',
                'has_meal_planning', 'has_nutrition_tracking',
                'has_analytics', 'has_advanced_analytics',
                'has_export', 'has_api_access',
                'has_ocr_receipts', 'has_voice_input',
                'has_priority_support'
            )
        }),
        ('Stripe Integration', {
            'fields': (
                'stripe_product_id', 'stripe_monthly_price_id',
                'stripe_yearly_price_id'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'plan_name', 'status', 'billing_period',
        'current_period_end', 'is_active_display'
    ]
    list_filter = ['status', 'plan__tier', 'billing_period']
    search_fields = ['user__email', 'stripe_subscription_id']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']
    
    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'plan', 'status', 'billing_period')
        }),
        ('Subscription Period', {
            'fields': (
                'current_period_start', 'current_period_end',
                'trial_start', 'trial_end', 'canceled_at'
            )
        }),
        ('Stripe Integration', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def plan_name(self, obj):
        return obj.plan.name
    plan_name.short_description = 'Plan'
    plan_name.admin_order_field = 'plan__name'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Inactive</span>'
        )
    is_active_display.short_description = 'Active'


@admin.register(BillingHistory)
class BillingHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'type', 'status', 'amount_display',
        'created_at', 'invoice_link'
    ]
    list_filter = ['type', 'status', 'created_at']
    search_fields = [
        'user__email', 'stripe_invoice_id', 
        'stripe_payment_intent_id', 'description'
    ]
    readonly_fields = ['created_at']
    raw_id_fields = ['user', 'subscription']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'user', 'subscription', 'type', 'status',
                'amount', 'currency', 'description'
            )
        }),
        ('Stripe Information', {
            'fields': (
                'stripe_invoice_id', 'stripe_payment_intent_id',
                'stripe_charge_id', 'invoice_url', 'invoice_pdf'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'paid_at')
        })
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def amount_display(self, obj):
        return f"${obj.amount} {obj.currency}"
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def invoice_link(self, obj):
        if obj.invoice_url:
            return format_html(
                '<a href="{}" target="_blank">View Invoice</a>',
                obj.invoice_url
            )
        return '-'
    invoice_link.short_description = 'Invoice'


@admin.register(InventoryUsage)
class InventoryUsageAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'item_count', 'last_updated', 'usage_bar']
    search_fields = ['user__email']
    readonly_fields = ['last_updated']
    raw_id_fields = ['user']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def usage_bar(self, obj):
        plan = obj.user.get_subscription_plan()
        if plan and plan.max_inventory_items:
            percentage = (obj.item_count / plan.max_inventory_items) * 100
            color = 'green' if percentage < 80 else 'orange' if percentage < 95 else 'red'
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0;">'
                '<div style="width: {}%; background-color: {}; height: 20px;"></div>'
                '</div> {}%',
                min(percentage, 100), color, int(percentage)
            )
        return 'Unlimited'
    usage_bar.short_description = 'Usage'


@admin.register(RecipeSearchUsage)
class RecipeSearchUsageAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'date', 'search_count', 'usage_display']
    list_filter = ['date']
    search_fields = ['user__email']
    date_hierarchy = 'date'
    raw_id_fields = ['user']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def usage_display(self, obj):
        plan = obj.user.get_subscription_plan()
        if plan and plan.max_recipes_per_day:
            return f"{obj.search_count} / {plan.max_recipes_per_day}"
        return f"{obj.search_count} / Unlimited"
    usage_display.short_description = 'Usage'


@admin.register(ShoppingListUsage)
class ShoppingListUsageAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'list_count', 'last_updated']
    search_fields = ['user__email']
    readonly_fields = ['last_updated']
    raw_id_fields = ['user']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'


@admin.register(ExportUsage)
class ExportUsageAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'export_type', 'export_format',
        'item_count', 'file_size_display', 'created_at'
    ]
    list_filter = ['export_type', 'export_format', 'created_at']
    search_fields = ['user__email']
    date_hierarchy = 'created_at'
    raw_id_fields = ['user']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def file_size_display(self, obj):
        # Convert bytes to human readable
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    file_size_display.short_description = 'File Size'