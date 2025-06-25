"""
Image processing utilities for recipes.
"""

import os
import uuid
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import requests
from io import BytesIO


def download_image_from_url(url, max_size_mb=5):
    """
    Download an image from URL and return as ContentFile.
    """
    try:
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            return None
        
        # Check file size
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > max_size_mb * 1024 * 1024:
            return None
        
        # Download image
        image_data = BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            image_data.write(chunk)
            if image_data.tell() > max_size_mb * 1024 * 1024:
                return None
        
        image_data.seek(0)
        
        # Generate filename
        extension = get_image_extension(content_type)
        filename = f"recipe_{uuid.uuid4().hex[:8]}{extension}"
        
        return ContentFile(image_data.read(), name=filename)
        
    except Exception as e:
        print(f"Error downloading image from {url}: {str(e)}")
        return None


def get_image_extension(content_type):
    """
    Get file extension from content type.
    """
    extensions = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
    }
    return extensions.get(content_type, '.jpg')


def process_recipe_image(image_file, max_width=800, max_height=600, quality=85):
    """
    Process and optimize recipe image.
    """
    try:
        # Open image
        with Image.open(image_file) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Auto-orient image based on EXIF data
            img = ImageOps.exif_transpose(img)
            
            # Resize if too large
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Save optimized image
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            # Generate new filename
            base_name = os.path.splitext(image_file.name)[0]
            new_filename = f"{base_name}_optimized.jpg"
            
            return ContentFile(output.read(), name=new_filename)
            
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return image_file  # Return original if processing fails


def create_recipe_thumbnail(image_file, size=(300, 200), quality=80):
    """
    Create a thumbnail for recipe image.
    """
    try:
        with Image.open(image_file) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Create thumbnail with cropping to maintain aspect ratio
            img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
            
            # Save thumbnail
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            # Generate thumbnail filename
            base_name = os.path.splitext(image_file.name)[0]
            thumb_filename = f"{base_name}_thumb.jpg"
            
            return ContentFile(output.read(), name=thumb_filename)
            
    except Exception as e:
        print(f"Error creating thumbnail: {str(e)}")
        return None


def validate_recipe_image(image_file, max_size_mb=10):
    """
    Validate uploaded recipe image.
    """
    errors = []
    
    # Check file size
    if image_file.size > max_size_mb * 1024 * 1024:
        errors.append(f"Image file too large. Maximum size is {max_size_mb}MB.")
    
    # Check file type
    try:
        with Image.open(image_file) as img:
            if img.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                errors.append("Unsupported image format. Please use JPEG, PNG, GIF, or WebP.")
            
            # Check dimensions
            if img.width < 100 or img.height < 100:
                errors.append("Image too small. Minimum size is 100x100 pixels.")
            
            if img.width > 4000 or img.height > 4000:
                errors.append("Image too large. Maximum size is 4000x4000 pixels.")
                
    except Exception:
        errors.append("Invalid image file.")
    
    return errors


def save_recipe_image_from_url(recipe, image_url):
    """
    Download and save recipe image from URL.
    """
    if not image_url:
        return False
    
    try:
        # Download image
        image_file = download_image_from_url(image_url)
        if not image_file:
            return False
        
        # Process and optimize
        processed_image = process_recipe_image(image_file)
        
        # Save to recipe
        recipe.image.save(
            processed_image.name,
            processed_image,
            save=True
        )
        
        return True
        
    except Exception as e:
        print(f"Error saving image from URL {image_url}: {str(e)}")
        return False


def get_recipe_image_url(recipe, size='medium'):
    """
    Get recipe image URL with fallback options.
    """
    # Try local image first
    if recipe.image:
        return recipe.image.url
    
    # Fallback to external image URL
    if recipe.image_url:
        return recipe.image_url
    
    # Fallback to placeholder
    placeholder_sizes = {
        'small': '300x200',
        'medium': '600x400',
        'large': '1200x800'
    }
    
    size_param = placeholder_sizes.get(size, '600x400')
    return f"https://via.placeholder.com/{size_param}/e2e8f0/6b7280?text=Recipe+Image"


def cleanup_old_images(days_old=30):
    """
    Clean up old unused recipe images.
    This should be run as a periodic task.
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Recipe
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    # Find recipes with images older than cutoff
    old_recipes = Recipe.objects.filter(
        created_at__lt=cutoff_date,
        image__isnull=False
    )
    
    deleted_count = 0
    
    for recipe in old_recipes:
        # Only delete if recipe is not public and has low engagement
        if not recipe.is_public and recipe.view_count < 5 and recipe.like_count < 2:
            try:
                if recipe.image:
                    # Delete the file
                    recipe.image.delete(save=False)
                    deleted_count += 1
            except Exception as e:
                print(f"Error deleting image for recipe {recipe.id}: {str(e)}")
    
    return deleted_count