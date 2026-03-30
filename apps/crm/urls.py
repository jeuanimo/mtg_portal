from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    # CRM Dashboard
    path('', views.crm_dashboard, name='dashboard'),
    path('pipeline/', views.pipeline_view, name='pipeline'),
    
    # Leads
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/create/', views.lead_create, name='lead_create'),
    path('leads/<int:pk>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:pk>/edit/', views.lead_edit, name='lead_edit'),
    path('leads/<int:pk>/status/', views.lead_update_status, name='lead_update_status'),
    path('leads/<int:pk>/convert/', views.lead_convert, name='lead_convert'),
    
    # Contacts
    path('contacts/', views.contact_list, name='contact_list'),
    path('contacts/create/', views.contact_create, name='contact_create'),
    path('contacts/<int:pk>/', views.contact_detail, name='contact_detail'),
    path('contacts/<int:pk>/edit/', views.contact_edit, name='contact_edit'),
    
    # Organizations
    path('organizations/', views.organization_list, name='organization_list'),
    path('organizations/create/', views.organization_create, name='organization_create'),
    path('organizations/<int:pk>/', views.organization_detail, name='organization_detail'),
    path('organizations/<int:pk>/edit/', views.organization_edit, name='organization_edit'),
    
    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/complete/', views.task_complete, name='task_complete'),
]
