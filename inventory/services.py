"""
External API services for product data enrichment.
"""
import logging
import requests
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify
import openfoodfacts
import uuid
from urllib.parse import urlparse
import os

from .models import Product, Category

logger = logging.getLogger(__name__)


class ProductDataService:
    """
    Service for fetching product data from external APIs.
    """
    
    def __init__(self):
        # Initialize Open Food Facts API with user agent
        self.off_api = openfoodfacts.API(
            user_agent="Kitchentory/1.0 (https://kitchentory.app)"
        )
        
    def lookup_product(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Look up product by barcode from multiple sources.
        Returns standardized product data or None if not found.
        """
        logger.info(f"Looking up product with barcode: {barcode}")
        
        # Try Open Food Facts first
        product_data = self._lookup_open_food_facts(barcode)
        if product_data:
            return product_data
            
        # Try UPC Database as fallback
        product_data = self._lookup_upc_database(barcode)
        if product_data:
            return product_data
            
        logger.warning(f"Product not found in any database: {barcode}")
        return None
    
    def _lookup_open_food_facts(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Look up product in Open Food Facts database.
        """
        try:
            logger.info(f"Searching Open Food Facts for barcode: {barcode}")
            
            # Query Open Food Facts API
            product = self.off_api.product.get(barcode)
            
            if not product or product.get('status') != 1:
                logger.info(f"Product not found in Open Food Facts: {barcode}")
                return None
            
            # Extract product data
            product_info = product.get('product', {})
            
            # Parse and standardize the data
            return self._parse_open_food_facts_data(product_info, barcode)
            
        except Exception as e:
            logger.error(f"Error querying Open Food Facts: {e}")
            return None
    
    def _parse_open_food_facts_data(self, product_info: Dict, barcode: str) -> Dict[str, Any]:
        """
        Parse Open Food Facts product data into standardized format.
        """
        # Extract basic product information
        name = product_info.get('product_name') or product_info.get('product_name_en', '')
        brand = product_info.get('brands', '').split(',')[0].strip() if product_info.get('brands') else ''
        
        # Extract category information
        categories = product_info.get('categories', '').split(',')
        main_category = categories[0].strip() if categories else 'Other'
        
        # Extract images
        image_url = self._get_best_image_url(product_info, 'front')
        thumbnail_url = self._get_best_image_url(product_info, 'front', size='200')
        
        # Extract nutritional information
        nutriments = product_info.get('nutriments', {})
        serving_size = product_info.get('serving_size')
        
        # Extract other metadata
        ingredients_text = product_info.get('ingredients_text_en') or product_info.get('ingredients_text', '')
        
        return {
            'source': 'openfoodfacts',
            'barcode': barcode,
            'name': name,
            'brand': brand,
            'category': main_category,
            'categories': categories,
            'image_url': image_url,
            'thumbnail_url': thumbnail_url,
            'serving_size': serving_size,
            'calories': nutriments.get('energy-kcal_100g'),
            'ingredients': ingredients_text,
            'description': product_info.get('generic_name') or '',
            'country': product_info.get('countries', ''),
            'packaging': product_info.get('packaging', ''),
            'labels': product_info.get('labels', ''),
            'stores': product_info.get('stores', ''),
            'verified': True,  # Open Food Facts data is generally reliable
            'raw_data': product_info  # Store raw data for debugging
        }
    
    def _get_best_image_url(self, product_info: Dict, image_type: str = 'front', size: str = '400') -> Optional[str]:
        """
        Get the best available image URL from Open Food Facts data.
        """
        # Try to get image in different sizes
        images = product_info.get('images', {})
        
        # Look for specific image type (front, ingredients, nutrition, etc.)
        image_key = f"{image_type}_{size}" if size else image_type
        
        # Try different image formats
        for key in [f"{image_key}", f"{image_type}_en", f"{image_type}"]:
            if key in images and images[key]:
                return images[key]
        
        # Fallback to any available image
        if 'front_url' in product_info:
            return product_info['front_url']
        
        # Look in selected_images
        selected_images = product_info.get('selected_images', {})
        if 'front' in selected_images:
            front_images = selected_images['front']
            if 'display' in front_images:
                return front_images['display'].get('en') or front_images['display'].get('fr')
        
        return None
    
    def _lookup_upc_database(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Look up product in UPC Database as fallback.
        Note: This is a basic implementation. You may want to use a paid service for better coverage.
        """
        try:
            logger.info(f"Searching UPC Database for barcode: {barcode}")
            
            # UPC Database API (free tier has limitations)
            url = f"https://api.upcitemdb.com/prod/trial/lookup"
            params = {'upc': barcode}
            headers = {'User-Agent': 'Kitchentory/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 'OK' and data.get('items'):
                    item = data['items'][0]
                    return self._parse_upc_database_data(item, barcode)
            
            logger.info(f"Product not found in UPC Database: {barcode}")
            return None
            
        except Exception as e:
            logger.error(f"Error querying UPC Database: {e}")
            return None
    
    def _parse_upc_database_data(self, item: Dict, barcode: str) -> Dict[str, Any]:
        """
        Parse UPC Database product data into standardized format.
        """
        name = item.get('title', '')
        brand = item.get('brand', '')
        category = item.get('category', 'Other')
        
        # UPC Database usually has limited image data
        images = item.get('images', [])
        image_url = images[0] if images else None
        
        return {
            'source': 'upcitemdb',
            'barcode': barcode,
            'name': name,
            'brand': brand,
            'category': category,
            'categories': [category] if category else [],
            'image_url': image_url,
            'thumbnail_url': image_url,  # Same image for now
            'serving_size': '',
            'calories': None,
            'ingredients': '',
            'description': item.get('description', ''),
            'packaging': '',
            'country': '',
            'verified': False,  # UPC Database data varies in quality
            'raw_data': item
        }
    
    def create_or_update_product(self, product_data: Dict[str, Any]) -> Optional[Product]:
        """
        Create or update a Product model instance from external API data.
        """
        try:
            barcode = product_data['barcode']
            name = product_data['name']
            
            if not name:
                logger.warning(f"Product name is empty for barcode {barcode}")
                return None
            
            # Get or create category
            category = self._get_or_create_category(product_data.get('category', 'Other'))
            
            # Create or update product
            product, created = Product.objects.get_or_create(
                barcode=barcode,
                defaults={
                    'name': name,
                    'brand': product_data.get('brand', ''),
                    'category': category,
                    'serving_size': product_data.get('serving_size') or '',
                    'calories': product_data.get('calories'),
                    'image_url': product_data.get('image_url') or None,
                    'thumbnail_url': product_data.get('thumbnail_url') or None,
                    'description': product_data.get('description', ''),
                    'ingredients': product_data.get('ingredients', ''),
                    'packaging': product_data.get('packaging', ''),
                    'country': product_data.get('country', ''),
                    'default_unit': 'count',  # Default unit
                    'source': product_data.get('source', 'external'),
                    'verified': product_data.get('verified', False),
                }
            )
            
            if not created:
                # Update existing product with newer data
                product.name = name
                product.brand = product_data.get('brand', product.brand)
                product.category = category
                product.serving_size = product_data.get('serving_size') or product.serving_size
                if product_data.get('calories'):
                    product.calories = product_data['calories']
                if product_data.get('image_url'):
                    product.image_url = product_data['image_url']
                if product_data.get('thumbnail_url'):
                    product.thumbnail_url = product_data['thumbnail_url']
                product.description = product_data.get('description') or product.description
                product.ingredients = product_data.get('ingredients') or product.ingredients
                product.packaging = product_data.get('packaging') or product.packaging
                product.country = product_data.get('country') or product.country
                product.source = product_data.get('source', product.source)
                product.verified = product_data.get('verified', product.verified)
                product.save()
            
            logger.info(f"{'Created' if created else 'Updated'} product: {product.name} ({barcode})")
            return product
            
        except Exception as e:
            logger.error(f"Error creating/updating product: {e}")
            return None
    
    def _get_or_create_category(self, category_name: str) -> Category:
        """
        Get or create a category by name.
        """
        if not category_name or category_name.lower() in ['', 'other', 'unknown']:
            category_name = 'Other'
        
        # Clean up category name
        category_name = category_name.strip().title()
        
        # Create slug from name
        slug = slugify(category_name.lower())
        
        # Get or create category
        category, created = Category.objects.get_or_create(
            slug=slug,
            defaults={
                'name': category_name,
                'color': Category.CATEGORY_COLORS.get(slug, '#6B7280')
            }
        )
        
        if created:
            logger.info(f"Created new category: {category_name}")
        
        return category
    
    def bulk_enrich_products(self, barcodes: List[str]) -> Dict[str, Any]:
        """
        Bulk enrich multiple products (for batch processing).
        """
        results = {
            'success': [],
            'failed': [],
            'total': len(barcodes)
        }
        
        for barcode in barcodes:
            try:
                product_data = self.lookup_product(barcode)
                if product_data:
                    product = self.create_or_update_product(product_data)
                    if product:
                        results['success'].append({
                            'barcode': barcode,
                            'product_id': product.id,
                            'name': product.name
                        })
                    else:
                        results['failed'].append({
                            'barcode': barcode,
                            'error': 'Failed to create product'
                        })
                else:
                    results['failed'].append({
                        'barcode': barcode,
                        'error': 'Product not found'
                    })
            except Exception as e:
                results['failed'].append({
                    'barcode': barcode,
                    'error': str(e)
                })
        
        logger.info(f"Bulk enrichment complete: {len(results['success'])}/{results['total']} successful")
        return results
    
    def download_product_image(self, image_url: str, product_name: str, image_type: str = 'product') -> Optional[str]:
        """
        Download product image from URL and save it locally.
        Returns the local file path or None if failed.
        """
        if not image_url:
            return None
            
        try:
            logger.info(f"Downloading image from: {image_url}")
            
            # Make request with timeout
            response = requests.get(
                image_url, 
                timeout=30,
                headers={'User-Agent': 'Kitchentory/1.0'}
            )
            response.raise_for_status()
            
            # Get file extension from URL or content type
            parsed_url = urlparse(image_url)
            file_ext = os.path.splitext(parsed_url.path)[1].lower()
            
            if not file_ext:
                content_type = response.headers.get('content-type', '').lower()
                if 'jpeg' in content_type or 'jpg' in content_type:
                    file_ext = '.jpg'
                elif 'png' in content_type:
                    file_ext = '.png'
                elif 'webp' in content_type:
                    file_ext = '.webp'
                else:
                    file_ext = '.jpg'  # Default
            
            # Generate unique filename
            filename = f"products/{image_type}_{uuid.uuid4().hex}{file_ext}"
            
            # Save image
            content = ContentFile(response.content)
            saved_path = default_storage.save(filename, content)
            
            logger.info(f"Saved image: {saved_path}")
            return saved_path
            
        except Exception as e:
            logger.error(f"Failed to download image {image_url}: {e}")
            return None
    
    def process_product_images(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download and process product images, updating URLs to local paths.
        """
        processed_data = product_data.copy()
        
        # Download main product image
        if product_data.get('image_url'):
            local_path = self.download_product_image(
                product_data['image_url'], 
                product_data.get('name', 'product'),
                'main'
            )
            if local_path:
                processed_data['local_image_path'] = local_path
                # Keep original URL as backup
                processed_data['original_image_url'] = product_data['image_url']
        
        # Download thumbnail image (if different from main image)
        if (product_data.get('thumbnail_url') and 
            product_data.get('thumbnail_url') != product_data.get('image_url')):
            local_path = self.download_product_image(
                product_data['thumbnail_url'], 
                product_data.get('name', 'product'),
                'thumb'
            )
            if local_path:
                processed_data['local_thumbnail_path'] = local_path
                processed_data['original_thumbnail_url'] = product_data['thumbnail_url']
        
        return processed_data
    
    def create_or_update_product_with_images(self, product_data: Dict[str, Any]) -> Optional[Product]:
        """
        Create or update product with image downloading.
        """
        # Process images if enabled
        if getattr(settings, 'KITCHENTORY_DOWNLOAD_IMAGES', False):
            product_data = self.process_product_images(product_data)
        
        return self.create_or_update_product(product_data)


# Global service instance
product_data_service = ProductDataService()