from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import date, timedelta

from .models import Product, InventoryItem, StorageLocation, Category


class ProductForm(forms.ModelForm):
    """Form for creating/editing products."""

    class Meta:
        model = Product
        fields = ["name", "brand", "category", "barcode", "image_url"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": _("Product name")}
            ),
            "brand": forms.TextInput(
                attrs={"class": "form-input", "placeholder": _("Brand (optional)")}
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "barcode": forms.TextInput(
                attrs={"class": "form-input", "placeholder": _("Barcode (optional)")}
            ),
            "image_url": forms.URLInput(
                attrs={"class": "form-input", "placeholder": _("Image URL (optional)")}
            ),
        }


class InventoryItemForm(forms.ModelForm):
    """Form for adding/editing inventory items."""

    # Additional fields for better UX
    expiration_preset = forms.ChoiceField(
        required=False,
        choices=[
            ("", _("Custom date")),
            ("3", _("3 days")),
            ("7", _("1 week")),
            ("14", _("2 weeks")),
            ("30", _("1 month")),
            ("90", _("3 months")),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "x-model": "expirationPreset",
                "@change": "updateExpirationDate()",
            }
        ),
    )

    class Meta:
        model = InventoryItem
        fields = [
            "product",
            "current_quantity",
            "unit",
            "location",
            "purchase_date",
            "expiration_date",
            "purchase_price",
            "notes",
        ]
        widgets = {
            "product": forms.Select(
                attrs={
                    "class": "form-select",
                    "x-data": "{}",
                    "@change": 'htmx.trigger($el, "product-changed")',
                }
            ),
            "current_quantity": forms.NumberInput(
                attrs={"class": "form-input", "step": "0.01", "min": "0"}
            ),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "purchase_date": forms.DateInput(
                attrs={"class": "form-input", "type": "date"}
            ),
            "expiration_date": forms.DateInput(
                attrs={"class": "form-input", "type": "date", "x-ref": "expirationDate"}
            ),
            "purchase_price": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": _("0.00"),
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": _("Additional notes (optional)"),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Set default purchase date to today
        if not self.instance.pk:
            self.fields["purchase_date"].initial = date.today()

        # Filter locations by user's household
        if user and user.household:
            self.fields["location"].queryset = StorageLocation.objects.filter(
                household=user.household
            )

        # Add empty choice for product
        self.fields["product"].empty_label = _("Select a product")

        # Order categories for better UX
        self.fields["product"].queryset = Product.objects.select_related(
            "category"
        ).order_by("category__order", "name")


class QuickAddForm(forms.Form):
    """Simplified form for quick product addition."""

    barcode = forms.CharField(required=False, widget=forms.HiddenInput())

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": _("Product name"),
                "autocomplete": "off",
                "x-model": "productName",
                "hx-get": "/inventory/search/",
                "hx-trigger": "keyup changed delay:500ms",
                "hx-target": "#search-results",
                "hx-indicator": "#search-spinner",
            }
        ),
    )

    brand = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": _("Brand (optional)")}
        ),
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    current_quantity = forms.DecimalField(
        initial=1,
        min_value=0,
        widget=forms.NumberInput(
            attrs={"class": "form-input", "step": "0.01", "min": "0"}
        ),
    )

    unit = forms.ChoiceField(
        choices=InventoryItem.QUANTITY_UNITS,
        initial="count",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    location = forms.ModelChoiceField(
        queryset=StorageLocation.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    days_until_expiration = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "form-input",
                "placeholder": _("Days until expiration"),
                "min": "0",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter locations by user's household
        if user and user.household:
            self.fields["location"].queryset = StorageLocation.objects.filter(
                household=user.household
            )
            # Set default location if only one exists
            locations = self.fields["location"].queryset
            if locations.count() == 1:
                self.fields["location"].initial = locations.first()


class StorageLocationForm(forms.ModelForm):
    """Form for creating/editing storage locations."""

    class Meta:
        model = StorageLocation
        fields = ["name", "location_type", "temperature", "notes"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": _("e.g., Main Fridge, Basement Freezer"),
                }
            ),
            "location_type": forms.Select(attrs={"class": "form-select"}),
            "temperature": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "step": "0.1",
                    "placeholder": _("°C (optional)"),
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": _("Additional notes (optional)"),
                }
            ),
        }


class BulkActionForm(forms.Form):
    """Form for bulk actions on inventory items."""

    ACTION_CHOICES = [
        ("consume", _("Mark as consumed")),
        ("move", _("Move to location")),
        ("delete", _("Delete items")),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(
            attrs={"class": "form-select", "@change": "showActionOptions()"}
        ),
    )

    location = forms.ModelChoiceField(
        queryset=StorageLocation.objects.none(),
        required=False,
        widget=forms.Select(
            attrs={"class": "form-select", "x-show": "action === 'move'"}
        ),
    )

    items = forms.CharField(widget=forms.HiddenInput(), required=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and user.household:
            self.fields["location"].queryset = StorageLocation.objects.filter(
                household=user.household
            )


class ManualProductForm(forms.ModelForm):
    """Form for manually adding products not found in external databases"""

    class Meta:
        model = Product
        fields = [
            "name",
            "brand",
            "barcode",
            "category",
            "default_unit",
            "serving_size",
            "calories",
            "description",
            "ingredients",
            "packaging",
            "country",
            "average_price",
            "shelf_life_days",
            "local_image",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter product name...",
                    "required": True,
                }
            ),
            "brand": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Enter brand name..."}
            ),
            "barcode": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter barcode number...",
                    "pattern": "[0-9]{8,13}",
                    "title": "Enter 8-13 digit barcode",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "default_unit": forms.Select(attrs={"class": "form-select"}),
            "serving_size": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "e.g., 100g, 1 cup, 1 piece",
                }
            ),
            "calories": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "min": "0",
                    "placeholder": "Calories per serving",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 3,
                    "placeholder": "Brief product description...",
                }
            ),
            "ingredients": forms.Textarea(
                attrs={
                    "class": "form-textarea",
                    "rows": 4,
                    "placeholder": "List of ingredients...",
                }
            ),
            "packaging": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "e.g., plastic bottle, glass jar",
                }
            ),
            "country": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Country of origin"}
            ),
            "average_price": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Average price",
                }
            ),
            "shelf_life_days": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "min": "1",
                    "placeholder": "Typical shelf life in days",
                }
            ),
            "local_image": forms.FileInput(
                attrs={"class": "form-input", "accept": "image/*"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set required fields
        self.fields["name"].required = True
        self.fields["category"].required = True

        # Add helpful labels and descriptions
        self.fields["barcode"].help_text = _("Optional: Enter barcode if available")
        self.fields["serving_size"].help_text = _(
            "Standard serving size for this product"
        )
        self.fields["calories"].help_text = _("Calories per serving (optional)")
        self.fields["shelf_life_days"].help_text = _(
            "How long the product typically lasts"
        )
        self.fields["local_image"].help_text = _(
            "Upload a photo of the product (optional)"
        )

        # Filter categories to only show active ones
        self.fields["category"].queryset = Category.objects.all().order_by("name")

    def clean_barcode(self):
        """Validate barcode format and uniqueness"""
        barcode = self.cleaned_data.get("barcode")

        if barcode:
            # Clean barcode (remove whitespace)
            barcode = barcode.strip()

            # Check format (8-13 digits)
            if not barcode.isdigit() or len(barcode) < 8 or len(barcode) > 13:
                raise forms.ValidationError(_("Barcode must be 8-13 digits"))

            # Check uniqueness (exclude current instance if editing)
            existing = Product.objects.filter(barcode=barcode)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise forms.ValidationError(
                    _("A product with this barcode already exists")
                )

        return barcode

    def save(self, commit=True):
        """Save product with additional metadata"""
        product = super().save(commit=False)

        # Set source and verification status for manual entries
        product.source = "manual"
        product.verified = True  # Manually entered products are considered verified

        if commit:
            product.save()

        return product
