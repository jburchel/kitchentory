from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    CategoryViewSet, ProductViewSet, StorageLocationViewSet, InventoryItemViewSet,
    bulk_add_items
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'locations', StorageLocationViewSet, basename='location')
router.register(r'items', InventoryItemViewSet, basename='item')

app_name = 'inventory_api'

urlpatterns = [
    path('', include(router.urls)),
    path('items/bulk_add_ext/', bulk_add_items, name='bulk_add_items'),
]