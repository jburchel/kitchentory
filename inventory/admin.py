from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from datetime import date, timedelta

from .models import Category, StorageLocation, Product, InventoryItem, ProductBarcode


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "color_display", "slug", "order")
    list_filter = ("parent",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")

    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; '
            'border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.color,
        )

    color_display.short_description = _("Color")


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "household", "location_type", "temperature")
    list_filter = ("location_type", "household")
    search_fields = ("name", "household__name")
    ordering = ("household", "name")


class ProductBarcodeInline(admin.TabularInline):
    model = ProductBarcode
    extra = 1
    fields = ("barcode", "package_size")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category", "barcode", "verified")
    list_filter = ("verified", "category", "source")
    search_fields = ("name", "brand", "barcode")
    inlines = [ProductBarcodeInline]
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "brand", "category", "barcode")}),
        (
            _("Nutritional Information"),
            {"fields": ("serving_size", "calories"), "classes": ("collapse",)},
        ),
        (
            _("Images"),
            {"fields": ("image_url", "thumbnail_url"), "classes": ("collapse",)},
        ),
        (_("Metadata"), {"fields": ("source", "verified", "created_at", "updated_at")}),
    )


class ExpiringItemFilter(admin.SimpleListFilter):
    title = _("expiration status")
    parameter_name = "expiring"

    def lookups(self, request, model_admin):
        return (
            ("expired", _("Expired")),
            ("today", _("Expires today")),
            ("week", _("Expires within 7 days")),
            ("month", _("Expires within 30 days")),
        )

    def queryset(self, request, queryset):
        today = date.today()
        if self.value() == "expired":
            return queryset.filter(expiration_date__lt=today)
        elif self.value() == "today":
            return queryset.filter(expiration_date=today)
        elif self.value() == "week":
            return queryset.filter(
                expiration_date__gte=today,
                expiration_date__lte=today + timedelta(days=7),
            )
        elif self.value() == "month":
            return queryset.filter(
                expiration_date__gte=today,
                expiration_date__lte=today + timedelta(days=30),
            )


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "product_name",
        "user",
        "quantity_display",
        "location",
        "expiration_status",
        "is_consumed",
    )
    list_filter = (
        "is_consumed",
        ExpiringItemFilter,
        "location",
        "location__location_type",
        "product__category",
    )
    search_fields = (
        "product__name",
        "product__brand",
        "user__email",
        "user__username",
        "notes",
    )
    date_hierarchy = "purchase_date"
    readonly_fields = ("id", "created_at", "updated_at", "consumed_date")

    fieldsets = (
        (None, {"fields": ("id", "user", "household", "product")}),
        (_("Quantity & Location"), {"fields": ("quantity", "unit", "location")}),
        (
            _("Dates"),
            {
                "fields": (
                    "purchase_date",
                    "expiration_date",
                    "opened_date",
                    "is_consumed",
                    "consumed_date",
                )
            },
        ),
        (_("Additional Information"), {"fields": ("price", "notes")}),
        (_("Metadata"), {"fields": ("created_at", "updated_at")}),
    )

    def product_name(self, obj):
        return obj.product.name

    product_name.short_description = _("Product")
    product_name.admin_order_field = "product__name"

    def quantity_display(self, obj):
        return f"{obj.quantity} {obj.get_unit_display()}"

    quantity_display.short_description = _("Quantity")

    def expiration_status(self, obj):
        if not obj.expiration_date:
            return "-"

        days = obj.days_until_expiration
        if days < 0:
            return format_html(
                '<span style="color: red;">Expired {} days ago</span>', abs(days)
            )
        elif days == 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">Expires today</span>'
            )
        elif days <= 7:
            return format_html(
                '<span style="color: orange;">Expires in {} days</span>', days
            )
        else:
            return f"Expires in {days} days"

    expiration_status.short_description = _("Expiration")
