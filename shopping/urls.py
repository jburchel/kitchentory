from django.urls import path
from . import views

app_name = 'shopping'

urlpatterns = [
    path('', views.shopping_dashboard, name='dashboard'),
    path('create/', views.create_shopping_list, name='create'),
    path('<uuid:list_id>/', views.shopping_list_detail, name='detail'),
]