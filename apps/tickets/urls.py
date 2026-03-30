from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.ticket_dashboard, name='dashboard'),
    
    # Tickets
    path('', views.ticket_list, name='ticket_list'),
    path('create/', views.ticket_create, name='ticket_create'),
    path('<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('<int:pk>/edit/', views.ticket_edit, name='ticket_edit'),
    path('<int:pk>/comment/', views.ticket_add_comment, name='ticket_add_comment'),
    path('<int:pk>/attachment/', views.ticket_add_attachment, name='ticket_add_attachment'),
    path('<int:pk>/status/', views.ticket_update_status, name='ticket_update_status'),
    path('<int:pk>/resolve/', views.ticket_resolve, name='ticket_resolve'),
    path('<int:pk>/close/', views.ticket_close, name='ticket_close'),
    path('<int:pk>/reopen/', views.ticket_reopen, name='ticket_reopen'),
    
    # Consulting Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/intake/', views.project_intake, name='project_intake'),
    path('projects/intake/', views.project_intake, name='project_intake_new'),
    
    # Deliverables
    path('deliverables/<int:pk>/', views.deliverable_detail, name='deliverable_detail'),
    path('projects/<int:project_pk>/deliverables/create/', views.deliverable_create, name='deliverable_create'),
    path('deliverables/<int:pk>/approve/', views.deliverable_approve, name='deliverable_approve'),
    
    # Change Requests
    path('projects/<int:project_pk>/change-request/', views.change_request_create, name='change_request_create'),
    path('change-requests/<int:pk>/review/', views.change_request_review, name='change_request_review'),
    
    # Time Entries
    path('time/', views.time_entry_list, name='time_entry_list'),
    path('time/log/', views.time_entry_create, name='time_entry_create'),
]
