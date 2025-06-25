from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.inventory_dashboard, name='dashboard'),
    
    # Inventory items
    path('items/', views.inventory_list, name='list'),
    path('add/', views.add_item, name='add'),
    path('item/<uuid:pk>/', views.item_detail, name='detail'),
    path('item/<uuid:pk>/consume/', views.consume_item, name='consume'),
    path('item/<uuid:pk>/delete/', views.delete_item, name='delete'),
    
    # AJAX endpoints
    path('search/', views.product_search, name='product_search'),
    path('search/category/<int:category_id>/', views.category_browse, name='category_browse'),
    path('barcode/', views.barcode_lookup, name='barcode_lookup'),
    
    # Storage locations
    path('locations/', views.storage_locations, name='storage_locations'),
    
    # Manual product addition
    path('add-product/', views.add_product_manual, name='add_product_manual'),
    path('add-item-for/<uuid:product_id>/', views.add_item_for_product, name='add_item_for_product'),
]