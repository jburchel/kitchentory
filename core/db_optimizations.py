"""
Database optimization utilities for Kitchentory.
"""

from django.db import models, connection
from django.core.cache import cache
from django.db.models import Prefetch, Q, Count, F, Sum
from django.db.models.query import QuerySet
from functools import wraps
import logging
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class OptimizedQuerySet(QuerySet):
    """Custom QuerySet with built-in optimizations."""
    
    def with_cache(self, timeout: int = 300, key_prefix: str = None):
        """Cache the queryset results."""
        if key_prefix is None:
            key_prefix = f"{self.model._meta.label_lower}"
        
        cache_key = f"{key_prefix}:{hash(str(self.query))}"
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = list(self)
        cache.set(cache_key, result, timeout)
        return result
    
    def select_related_smart(self, *fields):
        """Intelligently select related fields based on model relationships."""
        select_fields = []
        
        for field in fields:
            try:
                field_obj = self.model._meta.get_field(field)
                if hasattr(field_obj, 'related_model'):
                    select_fields.append(field)
            except:
                continue
        
        return self.select_related(*select_fields)
    
    def prefetch_related_smart(self, *fields):
        """Intelligently prefetch related fields."""
        prefetch_fields = []
        
        for field in fields:
            try:
                field_obj = self.model._meta.get_field(field)
                if hasattr(field_obj, 'related_model'):
                    prefetch_fields.append(field)
            except:
                continue
        
        return self.prefetch_related(*prefetch_fields)


class OptimizedManager(models.Manager):
    """Manager with built-in optimizations."""
    
    def get_queryset(self):
        return OptimizedQuerySet(self.model, using=self._db)
    
    def cached(self, timeout: int = 300):
        """Return a cached queryset."""
        return self.get_queryset().with_cache(timeout)


def query_debugger(func):
    """Decorator to debug and log query performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not logger.isEnabledFor(logging.DEBUG):
            return func(*args, **kwargs)
        
        initial_queries = len(connection.queries)
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        final_queries = len(connection.queries)
        
        query_count = final_queries - initial_queries
        execution_time = (end_time - start_time) * 1000
        
        logger.debug(
            f"Function {func.__name__} executed {query_count} queries "
            f"in {execution_time:.2f}ms"
        )
        
        if query_count > 10:  # Warning for high query counts
            logger.warning(
                f"High query count ({query_count}) in {func.__name__}. "
                "Consider optimization."
            )
        
        return result
    
    return wrapper


class DatabaseOptimizer:
    """Utility class for database optimizations."""
    
    @staticmethod
    def optimize_inventory_queries():
        """Pre-built optimizations for inventory queries."""
        from inventory.models import InventoryItem
        
        return InventoryItem.objects.select_related(
            'product',
            'product__category',
            'location',
            'household'
        ).prefetch_related(
            'product__barcodes',
            'expiration_alerts'
        )
    
    @staticmethod
    def optimize_recipe_queries():
        """Pre-built optimizations for recipe queries."""
        from recipes.models import Recipe
        
        return Recipe.objects.select_related(
            'category',
            'created_by'
        ).prefetch_related(
            Prefetch(
                'ingredients',
                queryset=Recipe.objects.select_related('product', 'product__category')
            ),
            'steps',
            'tags'
        )
    
    @staticmethod
    def optimize_shopping_queries():
        """Pre-built optimizations for shopping list queries."""
        from shopping.models import ShoppingList, ShoppingListItem
        
        return ShoppingList.objects.select_related(
            'created_by',
            'store'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=ShoppingListItem.objects.select_related(
                    'product',
                    'product__category'
                ).order_by('custom_order', 'created_at')
            ),
            'shared_with'
        )
    
    @staticmethod
    def get_user_inventory_stats(user, use_cache=True):
        """Get comprehensive inventory statistics with optimization."""
        cache_key = f"inventory_stats:{user.id}"
        
        if use_cache:
            cached_stats = cache.get(cache_key)
            if cached_stats:
                return cached_stats
        
        from inventory.models import InventoryItem
        from django.utils import timezone
        
        now = timezone.now()
        
        stats = InventoryItem.objects.filter(household__members=user).aggregate(
            total_items=Count('id'),
            total_value=Sum('estimated_value'),
            expiring_soon=Count(
                'id',
                filter=Q(expiration_date__lte=now + timezone.timedelta(days=7))
            ),
            expired_items=Count(
                'id',
                filter=Q(expiration_date__lt=now)
            ),
            low_stock=Count(
                'id',
                filter=Q(current_quantity__lte=F('minimum_threshold'))
            )
        )
        
        if use_cache:
            cache.set(cache_key, stats, 300)  # Cache for 5 minutes
        
        return stats
    
    @staticmethod
    def get_popular_recipes(user, limit=10, use_cache=True):
        """Get popular recipes with optimized queries."""
        cache_key = f"popular_recipes:{user.id}:{limit}"
        
        if use_cache:
            cached_recipes = cache.get(cache_key)
            if cached_recipes:
                return cached_recipes
        
        from recipes.models import Recipe, UserRecipeInteraction
        
        popular_recipes = Recipe.objects.filter(
            is_public=True
        ).annotate(
            interaction_count=Count('interactions'),
            avg_rating=models.Avg('interactions__rating')
        ).select_related(
            'category',
            'created_by'
        ).prefetch_related(
            'ingredients__product'
        ).order_by(
            '-interaction_count',
            '-avg_rating'
        )[:limit]
        
        recipes_list = list(popular_recipes)
        
        if use_cache:
            cache.set(cache_key, recipes_list, 1800)  # Cache for 30 minutes
        
        return recipes_list
    
    @staticmethod
    def bulk_update_inventory_quantities(updates: List[Dict]):
        """Efficiently update multiple inventory quantities."""
        from inventory.models import InventoryItem
        
        # Group updates by model for bulk operations
        items_to_update = []
        
        for update in updates:
            try:
                item = InventoryItem.objects.select_for_update().get(
                    id=update['id']
                )
                item.current_quantity = update['quantity']
                items_to_update.append(item)
            except InventoryItem.DoesNotExist:
                continue
        
        # Bulk update
        if items_to_update:
            InventoryItem.objects.bulk_update(
                items_to_update,
                ['current_quantity', 'updated_at']
            )
        
        return len(items_to_update)
    
    @staticmethod
    def cleanup_expired_cache_entries():
        """Clean up expired cache entries."""
        # This would typically be run as a management command
        from django.core.cache.utils import make_key
        
        # Clear specific pattern-based cache keys
        patterns = [
            'inventory_stats:*',
            'popular_recipes:*',
            'shopping_suggestions:*'
        ]
        
        # Note: This requires cache backend that supports pattern deletion
        # For Redis: cache.delete_pattern(pattern)
        # For other backends, you might need to track keys manually
        
        for pattern in patterns:
            try:
                cache.delete_pattern(pattern)
            except AttributeError:
                # Fallback for cache backends without pattern support
                pass
    
    @staticmethod
    def analyze_slow_queries(threshold_ms: float = 100):
        """Analyze slow queries from Django's query log."""
        if not logger.isEnabledFor(logging.DEBUG):
            logger.warning("Query logging is not enabled. Set DEBUG=True.")
            return
        
        slow_queries = []
        
        for query in connection.queries:
            time_ms = float(query['time']) * 1000
            if time_ms > threshold_ms:
                slow_queries.append({
                    'sql': query['sql'],
                    'time_ms': time_ms
                })
        
        if slow_queries:
            logger.warning(f"Found {len(slow_queries)} slow queries:")
            for query in slow_queries:
                logger.warning(f"  {query['time_ms']:.2f}ms: {query['sql'][:100]}...")
        
        return slow_queries
    
    @staticmethod
    def create_database_indexes():
        """Create additional database indexes for performance."""
        from django.db import connection
        
        indexes = [
            # Inventory optimizations
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS inventory_item_user_location ON inventory_inventoryitem(household_id, location_id);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS inventory_item_expiration ON inventory_inventoryitem(expiration_date) WHERE expiration_date IS NOT NULL;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS inventory_item_low_stock ON inventory_inventoryitem(current_quantity, minimum_threshold);",
            
            # Recipe optimizations
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS recipe_category_public ON recipes_recipe(category_id, is_public);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS recipe_created_rating ON recipes_recipe(created_at, average_rating);",
            
            # Shopping list optimizations
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS shopping_list_user_status ON shopping_shoppinglist(created_by_id, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS shopping_item_list_order ON shopping_shoppinglistitem(shopping_list_id, custom_order);",
            
            # Search optimizations (PostgreSQL specific)
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS product_search_gin ON inventory_product USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));",
        ]
        
        with connection.cursor() as cursor:
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    logger.info(f"Created index: {index_sql[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")


# Context manager for query optimization
class QueryOptimizer:
    """Context manager to temporarily optimize database queries."""
    
    def __init__(self, select_related=None, prefetch_related=None):
        self.select_related = select_related or []
        self.prefetch_related = prefetch_related or []
    
    def __enter__(self):
        # Store original query methods
        self._original_select_related = models.QuerySet.select_related
        self._original_prefetch_related = models.QuerySet.prefetch_related
        
        # Override with optimized versions
        def optimized_select_related(self, *fields):
            all_fields = list(fields) + self.select_related
            return self._original_select_related(*all_fields)
        
        def optimized_prefetch_related(self, *fields):
            all_fields = list(fields) + self.prefetch_related
            return self._original_prefetch_related(*all_fields)
        
        models.QuerySet.select_related = optimized_select_related
        models.QuerySet.prefetch_related = optimized_prefetch_related
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original methods
        models.QuerySet.select_related = self._original_select_related
        models.QuerySet.prefetch_related = self._original_prefetch_related


# Pagination helper
class OptimizedPaginator:
    """Memory-efficient paginator for large datasets."""
    
    def __init__(self, queryset, per_page, cursor_field='id'):
        self.queryset = queryset
        self.per_page = per_page
        self.cursor_field = cursor_field
    
    def get_page(self, cursor=None):
        """Get a page using cursor-based pagination."""
        qs = self.queryset
        
        if cursor:
            qs = qs.filter(**{f"{self.cursor_field}__gt": cursor})
        
        items = list(qs[:self.per_page + 1])  # Get one extra to check for next page
        
        has_next = len(items) > self.per_page
        if has_next:
            items = items[:-1]  # Remove the extra item
        
        next_cursor = getattr(items[-1], self.cursor_field) if items and has_next else None
        
        return {
            'items': items,
            'has_next': has_next,
            'next_cursor': next_cursor
        }