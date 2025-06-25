from django.urls import path, include
from . import views

app_name = 'recipes'

urlpatterns = [
    # Recipe listing and discovery
    path('', views.recipe_list, name='list'),
    
    # Recipe discovery system
    path('discovery/', include('recipes.discovery_urls')),
    
    # Recipe creation
    path('create/', views.recipe_create, name='create'),
    path('quick-create/', views.recipe_quick_create, name='quick_create'),
    path('import/', views.recipe_import, name='import'),
    
    # Recipe detail and editing
    path('<slug:slug>/', views.recipe_detail, name='detail'),
    path('<slug:slug>/edit/', views.recipe_edit, name='edit'),
    path('<slug:slug>/print/', views.recipe_print, name='print'),
    
    # Recipe interactions
    path('<slug:slug>/like/', views.recipe_like, name='like'),
]