"""
URL configuration for mtg_portal project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.core.views import health_check

urlpatterns = [
    # Health check for load balancers
    path('health/', health_check, name='health_check'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication (django-allauth)
    path('accounts/', include('allauth.urls')),
    
    # Local apps
    path('', include('apps.public.urls', namespace='public')),
    path('portal/', include('apps.core.urls', namespace='core')),
    path('profile/', include('apps.accounts.urls', namespace='accounts')),
    path('crm/', include('apps.crm.urls', namespace='crm')),
    path('invoicing/', include('apps.invoicing.urls', namespace='invoicing')),
    path('tickets/', include('apps.tickets.urls', namespace='tickets')),
    path('projects/', include('apps.projects.urls', namespace='projects')),
    path('meetings/', include('apps.meetings.urls', namespace='meetings')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('automations/', include('apps.automations.urls', namespace='automations')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Custom admin site header
admin.site.site_header = 'Mitchell Technology Group Admin'
admin.site.site_title = 'MTG Admin'
admin.site.index_title = 'Administration'
