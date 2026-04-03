from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.profile_view, name='profile'),
    path('edit/', views.profile_edit, name='profile_edit'),
    path('address/', views.profile_address, name='profile_address'),
    path('settings/', views.notification_settings, name='settings'),
    path('notifications/', views.notification_settings, name='notification_settings'),
    path('login-redirect/', views.after_login_redirect, name='login_redirect'),
]
