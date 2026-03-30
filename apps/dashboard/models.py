from django.db import models
# Dashboard app typically doesn't need models - it aggregates data from other apps
# But we can add some for storing dashboard preferences or cached stats

from apps.core.models import TimeStampedModel
from django.conf import settings


class DashboardWidget(TimeStampedModel):
    """User dashboard widget preferences."""
    
    class WidgetType(models.TextChoices):
        STATS = 'stats', 'Statistics'
        RECENT_TICKETS = 'recent_tickets', 'Recent Tickets'
        RECENT_INVOICES = 'recent_invoices', 'Recent Invoices'
        UPCOMING_MEETINGS = 'upcoming_meetings', 'Upcoming Meetings'
        PROJECT_PROGRESS = 'project_progress', 'Project Progress'
        LEAD_PIPELINE = 'lead_pipeline', 'Lead Pipeline'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_widgets'
    )
    widget_type = models.CharField(max_length=30, choices=WidgetType.choices)
    position = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Dashboard Widget'
        verbose_name_plural = 'Dashboard Widgets'
        ordering = ['position']
        unique_together = ['user', 'widget_type']
    
    def __str__(self):
        return f"{self.user.email} - {self.widget_type}"
