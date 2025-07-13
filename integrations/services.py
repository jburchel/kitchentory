"""
Import processing services for handling different data sources
"""

import csv
import pandas as pd
import logging
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db import transaction

from .models import ImportJob, ImportSource, ImportStatus, ParsedReceiptItem
from inventory.models import Product, Category, InventoryItem, StorageLocation
from inventory.serializers import QuickAddSerializer

logger = logging.getLogger(__name__)


class ImportService:
    """Service for processing import jobs"""

    def __init__(self):
        self.default_location = None

    def process_import_job(self, job_id: int) -> dict:
        """Process an import job and create inventory items"""
        try:
            job = ImportJob.objects.get(id=job_id)
            job.status = ImportStatus.PROCESSING
            job.save()

            # Get approved items
            approved_items = job.parsed_items.filter(
                is_approved=True, is_processed=False
            )

            created_count = 0
            failed_count = 0
            errors = []

            # Get or create default storage location
            self.default_location = self._get_default_location(job.household)

            with transaction.atomic():
                for item in approved_items:
                    try:
                        # Create inventory item
                        inventory_item = self._create_inventory_item(item, job)
                        if inventory_item:
                            item.is_processed = True
                            item.created_inventory_item_id = inventory_item.id
                            item.save()
                            created_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"Failed to create item: {item.name}")

                    except Exception as e:
                        failed_count += 1
                        error_msg = f"Error processing {item.name}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)

            # Update job status
            job.processed_items = created_count + failed_count
            job.created_items = created_count
            job.failed_items = failed_count

            if errors:
                job.errors = {"processing_errors": errors}

            if failed_count == 0:
                job.status = ImportStatus.COMPLETED
            else:
                job.status = (
                    ImportStatus.FAILED
                    if created_count == 0
                    else ImportStatus.COMPLETED
                )

            job.completed_at = timezone.now()
            job.save()

            return {
                "success": True,
                "created": created_count,
                "failed": failed_count,
                "errors": errors,
            }

        except ImportJob.DoesNotExist:
            return {"success": False, "error": "Import job not found"}
        except Exception as e:
            logger.error(f"Error processing import job {job_id}: {e}")
            return {"success": False, "error": str(e)}

    def process_csv_file(self, job_id: int, file) -> dict:
        """Process a CSV/Excel file for import"""
        try:
            job = ImportJob.objects.get(id=job_id)

            # Read file based on extension
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            elif file.name.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file)
            else:
                raise ValueError("Unsupported file format")

            # Parse and validate data
            items_data = self._parse_csv_data(df)

            # Store parsed data
            job.raw_data = {"csv_data": items_data[:1000]}  # Limit stored data
            job.total_items = len(items_data)
            job.save()

            # Create parsed items
            for i, item_data in enumerate(items_data):
                ParsedReceiptItem.objects.create(
                    import_job=job,
                    raw_text=str(item_data),
                    line_number=i + 1,
                    name=item_data.get("name", ""),
                    brand=item_data.get("brand", ""),
                    quantity=item_data.get("quantity", 1),
                    unit=item_data.get("unit", "item"),
                    price=item_data.get("price"),
                    confidence_score=item_data.get("confidence_score", 0.8),
                    store_name=item_data.get("store", ""),
                    purchase_date=item_data.get("purchase_date"),
                )

            job.status = ImportStatus.PENDING
            job.save()

            return {"success": True, "items_found": len(items_data)}

        except Exception as e:
            logger.error(f"Error processing CSV file: {e}")
            job.status = ImportStatus.FAILED
            job.errors = {"error": str(e)}
            job.save()
            return {"success": False, "error": str(e)}

    def _parse_csv_data(self, df: pd.DataFrame) -> list:
        """Parse CSV data into standardized format"""
        items = []

        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        column_mapping = self._get_column_mapping(df.columns.tolist())

        for index, row in df.iterrows():
            try:
                item_data = {
                    "name": self._get_value(row, column_mapping.get("name")),
                    "brand": self._get_value(row, column_mapping.get("brand")),
                    "quantity": self._parse_quantity(
                        self._get_value(row, column_mapping.get("quantity"))
                    ),
                    "unit": self._get_value(row, column_mapping.get("unit"), "item"),
                    "price": self._parse_price(
                        self._get_value(row, column_mapping.get("price"))
                    ),
                    "store": self._get_value(row, column_mapping.get("store")),
                    "purchase_date": self._parse_date(
                        self._get_value(row, column_mapping.get("date"))
                    ),
                    "confidence_score": 0.8,  # Default confidence for CSV imports
                }

                # Validate required fields
                if item_data["name"] and len(item_data["name"].strip()) > 0:
                    items.append(item_data)

            except Exception as e:
                logger.warning(f"Error parsing CSV row {index}: {e}")
                continue

        return items

    def _get_column_mapping(self, columns: list) -> dict:
        """Map CSV columns to standard fields"""
        mapping = {}

        # Common column name variations
        name_columns = [
            "name",
            "product",
            "item",
            "product_name",
            "item_name",
            "description",
        ]
        brand_columns = ["brand", "manufacturer", "brand_name"]
        quantity_columns = ["quantity", "qty", "amount", "count"]
        unit_columns = ["unit", "units", "measure", "uom"]
        price_columns = ["price", "cost", "amount", "total", "value"]
        store_columns = ["store", "shop", "retailer", "vendor", "merchant"]
        date_columns = ["date", "purchase_date", "bought_date", "order_date"]

        for col in columns:
            col_lower = col.lower()

            if col_lower in name_columns and "name" not in mapping:
                mapping["name"] = col
            elif col_lower in brand_columns and "brand" not in mapping:
                mapping["brand"] = col
            elif col_lower in quantity_columns and "quantity" not in mapping:
                mapping["quantity"] = col
            elif col_lower in unit_columns and "unit" not in mapping:
                mapping["unit"] = col
            elif col_lower in price_columns and "price" not in mapping:
                mapping["price"] = col
            elif col_lower in store_columns and "store" not in mapping:
                mapping["store"] = col
            elif col_lower in date_columns and "date" not in mapping:
                mapping["date"] = col

        return mapping

    def _get_value(self, row, column_name, default=""):
        """Get value from row with fallback"""
        if not column_name or column_name not in row:
            return default

        value = row[column_name]

        # Handle NaN values
        if pd.isna(value):
            return default

        return str(value).strip()

    def _parse_quantity(self, value: str) -> float:
        """Parse quantity from string"""
        if not value:
            return 1.0

        try:
            # Remove non-numeric characters except decimal point
            import re

            clean_value = re.sub(r"[^\d.]", "", str(value))
            return float(clean_value) if clean_value else 1.0
        except:
            return 1.0

    def _parse_price(self, value: str) -> float:
        """Parse price from string"""
        if not value:
            return None

        try:
            import re

            # Remove currency symbols and spaces
            clean_value = re.sub(r"[^\d.]", "", str(value))
            return float(clean_value) if clean_value else None
        except:
            return None

    def _parse_date(self, value: str) -> str:
        """Parse date from string"""
        if not value:
            return None

        try:
            # Try to parse common date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(str(value), fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
            return None
        except:
            return None

    def _create_inventory_item(
        self, parsed_item: ParsedReceiptItem, job: ImportJob
    ) -> InventoryItem:
        """Create an inventory item from parsed data"""
        try:
            # Find or create product
            product = self._find_or_create_product(
                parsed_item.name,
                parsed_item.brand,
                parsed_item.suggested_category or "Grocery",
            )

            if not product:
                logger.warning(f"Could not create product for: {parsed_item.name}")
                return None

            # Prepare inventory item data
            item_data = {
                "product_name": parsed_item.name,
                "quantity": float(parsed_item.quantity),
                "unit": parsed_item.unit,
                "location_id": (
                    self.default_location.id if self.default_location else None
                ),
                "purchase_date": parsed_item.purchase_date,
                "price_paid": float(parsed_item.price) if parsed_item.price else None,
                "notes": f"Imported from {job.get_source_display()}",
            }

            # Use QuickAddSerializer to create the item
            serializer = QuickAddSerializer(
                data=item_data,
                context={"request": type("obj", (object,), {"user": job.user})()},
            )

            if serializer.is_valid():
                return serializer.save()
            else:
                logger.error(
                    f"Serializer errors for {parsed_item.name}: {serializer.errors}"
                )
                return None

        except Exception as e:
            logger.error(f"Error creating inventory item for {parsed_item.name}: {e}")
            return None

    def _find_or_create_product(
        self, name: str, brand: str = "", category_name: str = "Grocery"
    ) -> Product:
        """Find existing product or create new one"""
        try:
            # Try to find existing product by name and brand
            search_name = name.strip().lower()
            search_brand = brand.strip().lower() if brand else ""

            # Search for existing products
            products = Product.objects.filter(
                name__icontains=search_name[:20]  # Partial match on first 20 chars
            )

            if search_brand:
                products = products.filter(brand__icontains=search_brand)

            if products.exists():
                return products.first()

            # Create new product
            category = self._find_or_create_category(category_name)

            product = Product.objects.create(
                name=name[:200],  # Limit name length
                brand=brand[:100] if brand else "",
                category=category,
                default_unit="item",
            )

            return product

        except Exception as e:
            logger.error(f"Error finding/creating product {name}: {e}")
            return None

    def _find_or_create_category(self, category_name: str) -> Category:
        """Find or create product category"""
        try:
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={"description": f"Auto-created category for {category_name}"},
            )
            return category
        except Exception as e:
            logger.error(f"Error creating category {category_name}: {e}")
            # Return default category
            return Category.objects.first()

    def _get_default_location(self, household) -> StorageLocation:
        """Get or create default storage location for household"""
        try:
            location, created = StorageLocation.objects.get_or_create(
                household=household,
                name="Pantry",
                defaults={
                    "location_type": "pantry",
                    "description": "Default storage location for imports",
                    "created_by": household.created_by,
                },
            )
            return location
        except Exception as e:
            logger.error(f"Error getting default location: {e}")
            return None


class CSVImportHelper:
    """Helper class for CSV import operations"""

    @staticmethod
    def validate_csv_format(file) -> dict:
        """Validate CSV file format and structure"""
        try:
            # Read first few rows
            if file.name.endswith(".csv"):
                df = pd.read_csv(file, nrows=5)
            else:
                df = pd.read_excel(file, nrows=5)

            # Check for required columns
            columns = df.columns.str.lower().str.strip().tolist()

            has_name = any(col in columns for col in ["name", "product", "item"])
            has_quantity = any(col in columns for col in ["quantity", "qty", "amount"])

            return {
                "valid": has_name,
                "columns": columns,
                "row_count": len(df),
                "has_name": has_name,
                "has_quantity": has_quantity,
                "suggestions": CSVImportHelper._get_format_suggestions(columns),
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    @staticmethod
    def _get_format_suggestions(columns: list) -> list:
        """Get format suggestions for CSV import"""
        suggestions = []

        if not any(col in columns for col in ["name", "product", "item"]):
            suggestions.append("Add a 'name' or 'product' column for item names")

        if not any(col in columns for col in ["quantity", "qty"]):
            suggestions.append("Add a 'quantity' column for item quantities")

        return suggestions
