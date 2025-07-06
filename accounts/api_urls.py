from django.urls import path
from . import api_views

app_name = 'accounts_api'

urlpatterns = [
    path('login/', api_views.login_api, name='login'),
    path('logout/', api_views.logout_api, name='logout'),
    path('user/', api_views.user_info, name='user_info'),
]