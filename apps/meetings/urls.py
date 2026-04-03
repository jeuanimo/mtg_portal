from django.urls import path
from . import views

app_name = 'meetings'

urlpatterns = [
    # Dashboard
    path('', views.meeting_dashboard, name='meeting_dashboard'),
    path('list/', views.meeting_list, name='meeting_list'),

    # Meeting CRUD
    path('create/', views.meeting_create, name='meeting_create'),
    path('quick/', views.quick_schedule, name='quick_schedule'),
    path('<int:pk>/', views.meeting_detail, name='meeting_detail'),
    path('<int:pk>/edit/', views.meeting_edit, name='meeting_edit'),

    # Meeting actions
    path('<int:pk>/cancel/', views.meeting_cancel, name='meeting_cancel'),
    path('<int:pk>/start/', views.meeting_start, name='meeting_start'),
    path('<int:pk>/complete/', views.meeting_complete, name='meeting_complete'),
    path('<int:pk>/notes/', views.meeting_update_notes, name='meeting_update_notes'),

    # Attendees
    path('<int:pk>/attendees/add/', views.meeting_add_attendee, name='meeting_add_attendee'),
    path('<int:pk>/attendees/<int:attendee_pk>/remove/', views.meeting_remove_attendee, name='meeting_remove_attendee'),

    # Recordings
    path('recordings/', views.recording_list, name='recording_list'),
    path('<int:pk>/recordings/sync/', views.sync_recordings, name='sync_recordings'),

    # Calendar
    path('calendar/', views.meeting_calendar, name='meeting_calendar'),

    # Availability
    path('availability/', views.availability_list, name='availability_list'),
    path('availability/<int:pk>/delete/', views.availability_delete, name='availability_delete'),

    # Client join (public)
    path('join/<uuid:token>/', views.client_join, name='client_join'),

    # HTMX endpoints
    path('htmx/contacts/', views.get_organization_contacts, name='get_organization_contacts'),
]
