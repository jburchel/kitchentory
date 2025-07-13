import logging
from django.db.models import Count, Q, Case, When, IntegerField
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from accounts.permissions import IsHouseholdMember, HouseholdQuerySetMixin

logger = logging.getLogger(__name__)

from .models import Category, Product, StorageLocation, InventoryItem
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    StorageLocationSerializer,
    InventoryItemSerializer,
    InventoryItemListSerializer,
    QuickAddSerializer,
    BulkActionSerializer,
)
from .services import product_data_service


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API viewset for categories.
    Provides list and retrieve actions only.
    """

    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "item_count"]
    ordering = ["name"]

    def get_queryset(self):
        return (
            Category.objects.select_related("parent")
            .prefetch_related("children")
            .annotate(
                item_count=Count(
                    "product__inventoryitem",
                    filter=Q(
                        product__inventoryitem__household=self.request.user.household
                    ),
                )
            )
        )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API viewset for products.
    Provides list, retrieve, and search functionality.
    """

    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "default_unit"]
    search_fields = ["name", "brand", "barcode"]
    ordering_fields = ["name", "brand", "average_price"]
    ordering = ["name"]

    def get_queryset(self):
        return Product.objects.select_related("category")

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Enhanced search endpoint with autocomplete support"""
        query = request.query_params.get("q", "")
        if len(query) < 2:
            return Response([])

        products = Product.objects.filter(
            Q(name__icontains=query) | Q(brand__icontains=query) | Q(barcode=query)
        ).select_related("category")[:10]

        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_barcode(self, request):
        """
        Lookup product by barcode.
        First checks local database, then external APIs if not found.
        """
        barcode = request.query_params.get("barcode")
        if not barcode:
            return Response(
                {"error": "Barcode parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Clean barcode (remove any whitespace)
        barcode = barcode.strip()

        try:
            # First try to find in local database
            product = Product.objects.select_related("category").get(barcode=barcode)
            serializer = self.get_serializer(product)
            return Response(serializer.data)

        except Product.DoesNotExist:
            # If not found locally, try external APIs
            try:
                product_data = product_data_service.lookup_product(barcode)

                if product_data:
                    # Create product from external data
                    product = product_data_service.create_or_update_product(
                        product_data
                    )

                    if product:
                        serializer = self.get_serializer(product)
                        return Response(
                            {
                                **serializer.data,
                                "newly_added": True,
                                "source": product_data.get("source", "external"),
                            }
                        )

                # Not found in any database
                return Response(
                    {
                        "error": "Product not found",
                        "barcode": barcode,
                        "suggestion": "You can add this product manually",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            except Exception as e:
                # Log error but don't expose internal details
                logger.error(f"Error looking up barcode {barcode}: {e}")
                return Response(
                    {
                        "error": "Unable to lookup product at this time",
                        "barcode": barcode,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

    @action(detail=False, methods=["post"])
    def enrich_products(self, request):
        """
        Bulk enrich products from external APIs.
        Expects: {'barcodes': ['123456789', '987654321', ...]}
        """
        barcodes = request.data.get("barcodes", [])

        if not barcodes or not isinstance(barcodes, list):
            return Response(
                {"error": "barcodes field required (list of barcode strings)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit to prevent abuse
        if len(barcodes) > 50:
            return Response(
                {"error": "Maximum 50 barcodes per request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            results = product_data_service.bulk_enrich_products(barcodes)
            return Response(results)
        except Exception as e:
            logger.error(f"Error in bulk product enrichment: {e}")
            return Response(
                {"error": "Bulk enrichment failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StorageLocationViewSet(viewsets.ModelViewSet):
    """
    API viewset for storage locations.
    Provides full CRUD operations for household-specific locations.
    """

    serializer_class = StorageLocationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "notes"]
    ordering_fields = ["name", "location_type", "item_count"]
    ordering = ["name"]

    def get_queryset(self):
        return StorageLocation.objects.filter(
            household=self.request.user.household
        ).annotate(item_count=Count("inventoryitem"))

    def perform_create(self, serializer):
        serializer.save(
            household=self.request.user.household, created_by=self.request.user
        )


@method_decorator(csrf_exempt, name="dispatch")
class InventoryItemViewSet(HouseholdQuerySetMixin, viewsets.ModelViewSet):
    """
    API viewset for inventory items.
    Provides full CRUD operations with filtering and bulk actions.
    """

    permission_classes = [IsAuthenticated, IsHouseholdMember]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["product__category", "location", "unit", "is_expired"]
    search_fields = ["product__name", "product__brand", "notes"]
    ordering_fields = [
        "created_at",
        "updated_at",
        "expiration_date",
        "product__name",
        "quantity",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        # Annotate with computed fields
        today = timezone.now().date()

        queryset = (
            InventoryItem.objects.filter(household=self.request.user.household)
            .select_related("product", "product__category", "location")
            .annotate(
                days_until_expiration=Case(
                    When(expiration_date__isnull=True, then=None),
                    default=Case(
                        When(expiration_date__lt=today, then=-1),
                        default=IntegerField("expiration_date") - today.toordinal(),
                        output_field=IntegerField(),
                    ),
                    output_field=IntegerField(),
                ),
                is_expired=Case(
                    When(expiration_date__isnull=True, then=False),
                    When(expiration_date__lt=today, then=True),
                    default=False,
                    output_field=IntegerField(),
                ),
            )
        )

        # Apply additional filters
        expiring_soon = self.request.query_params.get("expiring_soon")
        if expiring_soon:
            days = int(expiring_soon) if expiring_soon.isdigit() else 7
            queryset = queryset.filter(
                expiration_date__lte=today + timezone.timedelta(days=days),
                expiration_date__gte=today,
            )

        expired = self.request.query_params.get("expired")
        if expired == "true":
            queryset = queryset.filter(expiration_date__lt=today)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return InventoryItemListSerializer
        return InventoryItemSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=["post"])
    def quick_add(self, request):
        """Quick add endpoint for simple item creation"""
        serializer = QuickAddSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            item = serializer.save()
            response_serializer = InventoryItemSerializer(
                item, context={"request": request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=["post"])
    def bulk_add(self, request):
        """Bulk add endpoint for browser extension"""
        from django.utils import timezone
        from datetime import timedelta

        logger.info(
            f"bulk_add called by user: {request.user}, authenticated: {request.user.is_authenticated}"
        )
        logger.info(f"Request headers: {dict(request.headers)}")

        items_data = request.data.get("items", [])

        if not items_data or not isinstance(items_data, list):
            return Response(
                {"error": "items field required (list of item objects)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit to prevent abuse
        if len(items_data) > 100:
            return Response(
                {"error": "Maximum 100 items per request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_items = []
        errors = []

        # Get or create default category
        default_category, _ = Category.objects.get_or_create(
            name="Other", defaults={"slug": "other"}
        )

        # Get or create default location
        default_location, _ = StorageLocation.objects.get_or_create(
            household=request.user.household,
            name="Fridge",
            defaults={"location_type": "fridge", "created_by": request.user},
        )

        # Unit mapping for browser extension
        unit_mapping = {
            "item": "count",
            "items": "count",
            "each": "count",
            "piece": "count",
            "pieces": "count",
            "pack": "count",
            "package": "count",
            "count": "count",
            "lb": "lb",
            "lbs": "lb",
            "pound": "lb",
            "pounds": "lb",
            "oz": "oz",
            "ounce": "oz",
            "ounces": "oz",
            "g": "g",
            "gram": "g",
            "grams": "g",
            "kg": "kg",
            "kilogram": "kg",
            "kilograms": "kg",
            "ml": "ml",
            "milliliter": "ml",
            "milliliters": "ml",
            "l": "l",
            "liter": "l",
            "liters": "l",
            "cup": "cup",
            "cups": "cup",
            "tbsp": "tbsp",
            "tablespoon": "tbsp",
            "tablespoons": "tbsp",
            "tsp": "tsp",
            "teaspoon": "tsp",
            "teaspoons": "tsp",
        }

        for i, item_data in enumerate(items_data):
            try:
                # Normalize unit
                unit = item_data.get("unit", "item").lower().strip()
                normalized_unit = unit_mapping.get(unit, "count")

                # Get or create category
                category_name = item_data.get("category", "Other").strip()
                if category_name:
                    category, _ = Category.objects.get_or_create(
                        name=category_name.title(),
                        defaults={"slug": category_name.lower().replace(" ", "-")},
                    )
                else:
                    category = default_category

                # Get or create location
                location_name = item_data.get("location", "Fridge").strip()
                if location_name:
                    location, _ = StorageLocation.objects.get_or_create(
                        household=request.user.household,
                        name=location_name.title(),
                        defaults={"location_type": "other", "created_by": request.user},
                    )
                else:
                    location = default_location

                # Create or get product
                product_name = item_data.get("name", "").strip()
                if not product_name:
                    errors.append(
                        {
                            "index": i,
                            "item": "Unknown",
                            "error": "Product name is required",
                        }
                    )
                    continue

                brand = item_data.get("brand", "").strip()
                product, created = Product.objects.get_or_create(
                    name=product_name,
                    brand=brand,
                    defaults={
                        "category": category,
                        "default_unit": normalized_unit,
                        "barcode": item_data.get("barcode", "").strip(),
                    },
                )

                # Create inventory item
                inventory_item = InventoryItem.objects.create(
                    household=request.user.household,
                    product=product,
                    quantity=max(float(item_data.get("quantity", 1)), 0.01),
                    unit=normalized_unit,
                    location=location,
                    price_paid=(
                        float(item_data.get("price"))
                        if item_data.get("price")
                        else None
                    ),
                    notes=item_data.get("notes", ""),
                    added_by=request.user,
                )

                created_items.append(inventory_item)

            except Exception as e:
                logger.error(f"Error adding item {i}: {e}")
                errors.append(
                    {
                        "index": i,
                        "item": item_data.get("name", "Unknown"),
                        "error": str(e),
                    }
                )

        # Return results
        response_data = {
            "added": len(created_items),
            "total": len(items_data),
            "success": len(errors) == 0,
        }

        if errors:
            response_data["errors"] = errors

        if created_items:
            # Return serialized created items
            response_serializer = InventoryItemListSerializer(
                created_items, many=True, context={"request": request}
            )
            response_data["items"] = response_serializer.data

        status_code = (
            status.HTTP_201_CREATED if created_items else status.HTTP_400_BAD_REQUEST
        )
        return Response(response_data, status=status_code)

    @action(detail=False, methods=["post"])
    def bulk_action(self, request):
        """Bulk operations on inventory items"""
        serializer = BulkActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        item_ids = validated_data["item_ids"]
        action_type = validated_data["action"]

        # Get items and verify ownership
        items = InventoryItem.objects.filter(
            id__in=item_ids, household=request.user.household
        )

        if len(items) != len(item_ids):
            return Response(
                {"error": "Some items not found or not accessible"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Perform bulk action
        if action_type == "consume":
            count = items.delete()[0]
            return Response({"message": f"{count} items marked as consumed"})

        elif action_type == "delete":
            count = items.delete()[0]
            return Response({"message": f"{count} items deleted"})

        elif action_type == "update_location":
            location_id = validated_data.get("location_id")
            count = items.update(location_id=location_id)
            return Response({"message": f"{count} items updated"})

        elif action_type == "update_expiration":
            expiration_date = validated_data.get("expiration_date")
            count = items.update(expiration_date=expiration_date)
            return Response({"message": f"{count} items updated"})

        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def consume(self, request, pk=None):
        """Mark a single item as consumed (delete it)"""
        item = self.get_object()
        item.delete()
        return Response({"message": "Item marked as consumed"})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get inventory statistics"""
        today = timezone.now().date()
        queryset = self.get_queryset()

        total_items = queryset.count()
        expired_items = queryset.filter(expiration_date__lt=today).count()
        expiring_soon = queryset.filter(
            expiration_date__lte=today + timezone.timedelta(days=7),
            expiration_date__gte=today,
        ).count()

        categories = (
            queryset.values("product__category__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        locations = (
            queryset.values("location__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        return Response(
            {
                "total_items": total_items,
                "expired_items": expired_items,
                "expiring_soon": expiring_soon,
                "top_categories": categories,
                "top_locations": locations,
            }
        )

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        """Get items expiring soon"""
        days = int(request.query_params.get("days", 7))
        today = timezone.now().date()

        items = (
            self.get_queryset()
            .filter(
                expiration_date__lte=today + timezone.timedelta(days=days),
                expiration_date__gte=today,
            )
            .order_by("expiration_date")
        )

        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def expired(self, request):
        """Get expired items"""
        today = timezone.now().date()

        items = (
            self.get_queryset()
            .filter(expiration_date__lt=today)
            .order_by("expiration_date")
        )

        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_add_items(request):
    """Standalone bulk add endpoint for browser extension"""
    from django.utils import timezone
    from datetime import timedelta

    logger.info(
        f"bulk_add_items called by user: {request.user}, authenticated: {request.user.is_authenticated}"
    )
    logger.info(f"Request headers: {dict(request.headers)}")

    items_data = request.data.get("items", [])

    if not items_data or not isinstance(items_data, list):
        return Response(
            {"error": "items field required (list of item objects)"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Limit to prevent abuse
    if len(items_data) > 100:
        return Response(
            {"error": "Maximum 100 items per request"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    created_items = []
    errors = []

    # Get or create default category
    default_category, _ = Category.objects.get_or_create(
        name="Other", defaults={"slug": "other"}
    )

    # Get or create default location
    default_location, _ = StorageLocation.objects.get_or_create(
        household=request.user.household,
        name="Fridge",
        defaults={"location_type": "fridge", "created_by": request.user},
    )

    # Unit mapping for browser extension
    unit_mapping = {
        "item": "count",
        "items": "count",
        "each": "count",
        "piece": "count",
        "pieces": "count",
        "pack": "count",
        "package": "count",
        "count": "count",
        "lb": "lb",
        "lbs": "lb",
        "pound": "lb",
        "pounds": "lb",
        "oz": "oz",
        "ounce": "oz",
        "ounces": "oz",
        "g": "g",
        "gram": "g",
        "grams": "g",
        "kg": "kg",
        "kilogram": "kg",
        "kilograms": "kg",
        "ml": "ml",
        "milliliter": "ml",
        "milliliters": "ml",
        "l": "l",
        "liter": "l",
        "liters": "l",
        "cup": "cup",
        "cups": "cup",
        "tbsp": "tbsp",
        "tablespoon": "tbsp",
        "tablespoons": "tbsp",
        "tsp": "tsp",
        "teaspoon": "tsp",
        "teaspoons": "tsp",
    }

    for i, item_data in enumerate(items_data):
        try:
            # Normalize unit
            unit = item_data.get("unit", "item").lower().strip()
            normalized_unit = unit_mapping.get(unit, "count")

            # Get or create category
            category_name = item_data.get("category", "Other").strip()
            if category_name:
                category, _ = Category.objects.get_or_create(
                    name=category_name.title(),
                    defaults={"slug": category_name.lower().replace(" ", "-")},
                )
            else:
                category = default_category

            # Get or create location
            location_name = item_data.get("location", "Fridge").strip()
            if location_name:
                location, _ = StorageLocation.objects.get_or_create(
                    household=request.user.household,
                    name=location_name.title(),
                    defaults={"location_type": "other", "created_by": request.user},
                )
            else:
                location = default_location

            # Create or get product
            product_name = item_data.get("name", "").strip()
            if not product_name:
                errors.append(
                    {"index": i, "item": "Unknown", "error": "Product name is required"}
                )
                continue

            brand = item_data.get("brand", "").strip()
            product, created = Product.objects.get_or_create(
                name=product_name,
                brand=brand,
                defaults={
                    "category": category,
                    "default_unit": normalized_unit,
                    "barcode": item_data.get("barcode", "").strip(),
                },
            )

            # Create inventory item
            inventory_item = InventoryItem.objects.create(
                household=request.user.household,
                product=product,
                quantity=max(float(item_data.get("quantity", 1)), 0.01),
                unit=normalized_unit,
                location=location,
                price_paid=(
                    float(item_data.get("price")) if item_data.get("price") else None
                ),
                notes=item_data.get("notes", ""),
                added_by=request.user,
            )

            created_items.append(inventory_item)

        except Exception as e:
            logger.error(f"Error adding item {i}: {e}")
            errors.append(
                {"index": i, "item": item_data.get("name", "Unknown"), "error": str(e)}
            )

    # Return results
    response_data = {
        "added": len(created_items),
        "total": len(items_data),
        "success": len(errors) == 0,
    }

    if errors:
        response_data["errors"] = errors

    if created_items:
        # Return basic item info
        response_data["items"] = [
            {
                "id": item.id,
                "name": item.product.name,
                "quantity": item.quantity,
                "unit": item.unit,
            }
            for item in created_items
        ]

    status_code = (
        status.HTTP_201_CREATED if created_items else status.HTTP_400_BAD_REQUEST
    )
    return Response(response_data, status=status_code)
