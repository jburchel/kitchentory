from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from inventory.models import Product


class Command(BaseCommand):
    help = "Update search vectors for all products"

    def handle(self, *args, **options):
        self.stdout.write("Updating search vectors for all products...")

        # Update all existing products with search vectors
        Product.objects.update(
            search_vector=(
                SearchVector("name", weight="A")
                + SearchVector("brand", weight="B")
                + SearchVector("description", weight="C")
            )
        )

        product_count = Product.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated search vectors for {product_count} products"
            )
        )
