"""
Comprehensive caching strategy for Kitchentory.
"""

import hashlib
import json
import pickle
from datetime import timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Union

from django.core.cache import cache
from django.core.cache.utils import make_key
from django.conf import settings
from django.db.models import Model
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class CacheManager:
    """Centralized cache management for the application."""
    
    # Cache timeouts (in seconds)
    TIMEOUTS = {
        'short': 300,      # 5 minutes
        'medium': 1800,    # 30 minutes
        'long': 3600,      # 1 hour
        'daily': 86400,    # 24 hours
        'weekly': 604800,  # 7 days
    }
    
    # Cache key prefixes
    PREFIXES = {
        'user_stats': 'user_stats',
        'inventory': 'inventory',
        'recipes': 'recipes',
        'shopping': 'shopping',
        'api': 'api',
        'search': 'search',
        'suggestions': 'suggestions',
        'analytics': 'analytics',
        'notifications': 'notifications',
    }
    
    @classmethod
    def get_key(cls, prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key."""
        key_parts = [cls.PREFIXES.get(prefix, prefix)]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, Model):
                key_parts.append(f"{arg._meta.label_lower}_{arg.pk}")
            elif isinstance(arg, (int, str)):
                key_parts.append(str(arg))
            else:
                # Hash complex objects
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}_{value}")
        
        return ":".join(key_parts)
    
    @classmethod
    def get(cls, key: str, default=None):
        """Get value from cache."""
        return cache.get(key, default)
    
    @classmethod
    def set(cls, key: str, value: Any, timeout: Union[str, int] = 'medium'):
        """Set value in cache."""
        if isinstance(timeout, str):
            timeout = cls.TIMEOUTS.get(timeout, cls.TIMEOUTS['medium'])
        
        return cache.set(key, value, timeout)
    
    @classmethod
    def delete(cls, key: str):
        """Delete key from cache."""
        return cache.delete(key)
    
    @classmethod
    def delete_pattern(cls, pattern: str):
        """Delete keys matching pattern (Redis only)."""
        try:
            return cache.delete_pattern(pattern)
        except AttributeError:
            # Fallback for non-Redis backends
            # This is less efficient but works with any backend
            from django.core.cache import caches
            default_cache = caches['default']
            if hasattr(default_cache, '_cache'):  # Memcached
                default_cache._cache.flush_all()
            return True
    
    @classmethod
    def invalidate_user_cache(cls, user_id: int):
        """Invalidate all cache entries for a specific user."""
        patterns = [
            f"{cls.PREFIXES['user_stats']}:{user_id}:*",
            f"{cls.PREFIXES['inventory']}:{user_id}:*",
            f"{cls.PREFIXES['recipes']}:{user_id}:*",
            f"{cls.PREFIXES['shopping']}:{user_id}:*",
            f"{cls.PREFIXES['suggestions']}:{user_id}:*",
        ]
        
        for pattern in patterns:
            cls.delete_pattern(pattern)
    
    @classmethod
    def warm_user_cache(cls, user: User):
        """Pre-populate cache with frequently accessed user data."""
        from core.db_optimizations import DatabaseOptimizer
        
        # Warm up user stats
        stats_key = cls.get_key('user_stats', user.id)
        if not cls.get(stats_key):
            stats = DatabaseOptimizer.get_user_inventory_stats(user, use_cache=False)
            cls.set(stats_key, stats, 'medium')
        
        # Warm up popular recipes
        recipes_key = cls.get_key('recipes', 'popular', user.id)
        if not cls.get(recipes_key):
            recipes = DatabaseOptimizer.get_popular_recipes(user, use_cache=False)
            cls.set(recipes_key, recipes, 'long')


def cached_function(timeout: Union[str, int] = 'medium', key_prefix: str = None):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                prefix = key_prefix
            else:
                prefix = f"func_{func.__module__}_{func.__name__}"
            
            cache_key = CacheManager.get_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            result = CacheManager.get(cache_key)
            if result is not None:
                return result
            
            # Calculate and cache result
            result = func(*args, **kwargs)
            CacheManager.set(cache_key, result, timeout)
            
            return result
        
        return wrapper
    return decorator


def cached_property_with_ttl(ttl: Union[str, int] = 'medium'):
    """Property decorator that caches the result with TTL."""
    def decorator(func):
        cache_attr = f"_cached_{func.__name__}"
        cache_time_attr = f"_cached_time_{func.__name__}"
        
        @property
        @wraps(func)
        def wrapper(self):
            now = timezone.now()
            
            # Check if we have a cached value and it's still valid
            if hasattr(self, cache_attr) and hasattr(self, cache_time_attr):
                cached_time = getattr(self, cache_time_attr)
                ttl_seconds = CacheManager.TIMEOUTS.get(ttl, ttl)
                
                if (now - cached_time).total_seconds() < ttl_seconds:
                    return getattr(self, cache_attr)
            
            # Calculate and cache new value
            result = func(self)
            setattr(self, cache_attr, result)
            setattr(self, cache_time_attr, now)
            
            return result
        
        return wrapper
    return decorator


class ModelCacheMixin:
    """Mixin to add caching capabilities to Django models."""
    
    CACHE_TIMEOUT = 'medium'
    
    def get_cache_key(self, suffix: str = '') -> str:
        """Get cache key for this model instance."""
        key_parts = [self._meta.label_lower, str(self.pk)]
        if suffix:
            key_parts.append(suffix)
        return ":".join(key_parts)
    
    def cache_set(self, key: str, value: Any, timeout: Union[str, int] = None):
        """Set cache value for this instance."""
        if timeout is None:
            timeout = self.CACHE_TIMEOUT
        return CacheManager.set(key, value, timeout)
    
    def cache_get(self, key: str, default=None):
        """Get cache value for this instance."""
        return CacheManager.get(key, default)
    
    def cache_delete(self, key: str = None):
        """Delete cache entries for this instance."""
        if key:
            return CacheManager.delete(key)
        else:
            # Delete all cache entries for this instance
            pattern = f"{self.get_cache_key()}*"
            return CacheManager.delete_pattern(pattern)
    
    def save(self, *args, **kwargs):
        """Override save to invalidate cache."""
        super().save(*args, **kwargs)
        self.cache_delete()
    
    def delete(self, *args, **kwargs):
        """Override delete to invalidate cache."""
        self.cache_delete()
        super().delete(*args, **kwargs)


class ApiResponseCache:
    """Cache for API responses with versioning support."""
    
    @staticmethod
    def get_key(request, view_name: str = None) -> str:
        """Generate cache key for API request."""
        key_parts = ['api']
        
        if view_name:
            key_parts.append(view_name)
        else:
            key_parts.append(request.resolver_match.view_name)
        
        # Add user ID if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            key_parts.append(f"user_{request.user.id}")
        
        # Add query parameters (sorted for consistency)
        if request.GET:
            query_hash = hashlib.md5(
                "&".join(f"{k}={v}" for k, v in sorted(request.GET.items())).encode()
            ).hexdigest()[:8]
            key_parts.append(f"query_{query_hash}")
        
        return ":".join(key_parts)
    
    @staticmethod
    def cache_response(key: str, response_data: Dict, timeout: Union[str, int] = 'short'):
        """Cache API response with metadata."""
        cache_data = {
            'data': response_data,
            'timestamp': timezone.now().isoformat(),
            'version': getattr(settings, 'API_VERSION', '1.0')
        }
        
        return CacheManager.set(key, cache_data, timeout)
    
    @staticmethod
    def get_cached_response(key: str) -> Optional[Dict]:
        """Get cached API response."""
        cached_data = CacheManager.get(key)
        
        if cached_data and isinstance(cached_data, dict):
            # Check if version matches
            cached_version = cached_data.get('version')
            current_version = getattr(settings, 'API_VERSION', '1.0')
            
            if cached_version == current_version:
                return cached_data.get('data')
        
        return None


def cache_api_response(timeout: Union[str, int] = 'short', key_func=None):
    """Decorator to cache API responses."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                cache_key = ApiResponseCache.get_key(request)
            
            # Try to get cached response
            cached_response = ApiResponseCache.get_cached_response(cache_key)
            if cached_response is not None:
                from django.http import JsonResponse
                return JsonResponse(cached_response)
            
            # Execute view and cache response
            response = view_func(request, *args, **kwargs)
            
            if hasattr(response, 'data') and response.status_code == 200:
                ApiResponseCache.cache_response(cache_key, response.data, timeout)
            
            return response
        
        return wrapper
    return decorator


class SearchCache:
    """Specialized cache for search results."""
    
    @staticmethod
    def get_search_key(query: str, filters: Dict = None, user_id: int = None) -> str:
        """Generate cache key for search query."""
        key_parts = ['search']
        
        # Normalize query
        normalized_query = query.lower().strip()
        query_hash = hashlib.md5(normalized_query.encode()).hexdigest()[:8]
        key_parts.append(f"q_{query_hash}")
        
        # Add filters
        if filters:
            filter_hash = hashlib.md5(
                json.dumps(filters, sort_keys=True).encode()
            ).hexdigest()[:8]
            key_parts.append(f"f_{filter_hash}")
        
        # Add user context
        if user_id:
            key_parts.append(f"u_{user_id}")
        
        return ":".join(key_parts)
    
    @staticmethod
    @cached_function(timeout='medium', key_prefix='search')
    def search_products(query: str, filters: Dict = None, user_id: int = None) -> List[Dict]:
        """Cached product search."""
        # This would be implemented in the actual search service
        pass
    
    @staticmethod
    @cached_function(timeout='long', key_prefix='search')
    def search_recipes(query: str, filters: Dict = None, user_id: int = None) -> List[Dict]:
        """Cached recipe search."""
        # This would be implemented in the actual search service
        pass


class CacheWarmer:
    """Utilities to warm up the cache proactively."""
    
    @staticmethod
    def warm_popular_content():
        """Warm cache with popular content."""
        from recipes.models import Recipe
        from inventory.models import Product
        
        # Cache popular recipes
        popular_recipes_key = CacheManager.get_key('recipes', 'popular_global')
        if not CacheManager.get(popular_recipes_key):
            popular_recipes = list(
                Recipe.objects.filter(is_public=True)
                .select_related('category', 'created_by')
                .prefetch_related('ingredients__product')
                .order_by('-view_count', '-average_rating')[:50]
            )
            CacheManager.set(popular_recipes_key, popular_recipes, 'daily')
        
        # Cache frequently searched products
        popular_products_key = CacheManager.get_key('products', 'popular')
        if not CacheManager.get(popular_products_key):
            popular_products = list(
                Product.objects.select_related('category')
                .order_by('-search_count')[:100]
            )
            CacheManager.set(popular_products_key, popular_products, 'daily')
    
    @staticmethod
    def warm_user_specific_cache(user: User):
        """Warm cache with user-specific data."""
        CacheManager.warm_user_cache(user)
    
    @staticmethod
    def scheduled_cache_warmup():
        """Scheduled task to warm up caches."""
        # This would be called by a cron job or Celery task
        CacheWarmer.warm_popular_content()
        
        # Warm cache for active users
        active_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=7)
        )[:100]  # Limit to most recent 100 users
        
        for user in active_users:
            CacheWarmer.warm_user_specific_cache(user)


# Cache invalidation utilities
class CacheInvalidator:
    """Utilities for intelligent cache invalidation."""
    
    @staticmethod
    def invalidate_inventory_cache(user_id: int, product_id: int = None):
        """Invalidate inventory-related cache entries."""
        patterns = [
            f"{CacheManager.PREFIXES['inventory']}:{user_id}:*",
            f"{CacheManager.PREFIXES['user_stats']}:{user_id}:*",
            f"{CacheManager.PREFIXES['suggestions']}:{user_id}:*",
        ]
        
        if product_id:
            patterns.append(f"*product_{product_id}*")
        
        for pattern in patterns:
            CacheManager.delete_pattern(pattern)
    
    @staticmethod
    def invalidate_recipe_cache(recipe_id: int = None, user_id: int = None):
        """Invalidate recipe-related cache entries."""
        patterns = [
            f"{CacheManager.PREFIXES['recipes']}:*",
            f"{CacheManager.PREFIXES['search']}:*",
        ]
        
        if recipe_id:
            patterns.append(f"*recipe_{recipe_id}*")
        
        if user_id:
            patterns.append(f"{CacheManager.PREFIXES['recipes']}:{user_id}:*")
        
        for pattern in patterns:
            CacheManager.delete_pattern(pattern)
    
    @staticmethod
    def invalidate_shopping_cache(user_id: int, list_id: int = None):
        """Invalidate shopping list cache entries."""
        patterns = [
            f"{CacheManager.PREFIXES['shopping']}:{user_id}:*",
            f"{CacheManager.PREFIXES['suggestions']}:{user_id}:*",
        ]
        
        if list_id:
            patterns.append(f"*shopping_list_{list_id}*")
        
        for pattern in patterns:
            CacheManager.delete_pattern(pattern)