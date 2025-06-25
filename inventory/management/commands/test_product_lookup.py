"""
Management command to test product lookup from external APIs.
"""
from django.core.management.base import BaseCommand
from inventory.services import product_data_service


class Command(BaseCommand):
    help = 'Test product lookup from external APIs'

    def add_arguments(self, parser):
        parser.add_argument(
            'barcode',
            type=str,
            help='Barcode to lookup'
        )
        parser.add_argument(
            '--create',
            action='store_true',
            help='Create product in database if found'
        )

    def handle(self, *args, **options):
        barcode = options['barcode']
        create = options['create']
        
        self.stdout.write(f"Looking up barcode: {barcode}")
        
        # Test product lookup
        product_data = product_data_service.lookup_product(barcode)
        
        if product_data:
            self.stdout.write(
                self.style.SUCCESS(f"Found product: {product_data['name']}")
            )
            
            # Display product details
            for key, value in product_data.items():
                if key != 'raw_data':  # Skip raw data for readability
                    self.stdout.write(f"  {key}: {value}")
            
            # Create product if requested
            if create:
                product = product_data_service.create_or_update_product(product_data)
                if product:
                    self.stdout.write(
                        self.style.SUCCESS(f"Created product with ID: {product.id}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR("Failed to create product")
                    )
        else:
            self.stdout.write(
                self.style.ERROR(f"Product not found for barcode: {barcode}")
            )