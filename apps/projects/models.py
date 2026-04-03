from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.crm.models import Organization


class Project(TimeStampedModel):
    """Client projects."""
    
    class Status(models.TextChoices):
        PLANNING = 'planning', 'Planning'
        IN_PROGRESS = 'in_progress', 'In Progress'
        ON_HOLD = 'on_hold', 'On Hold'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='projects'
    )
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)
    
    # Dates
    start_date = models.DateField(null=True, blank=True)
    target_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Budget
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Team
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_projects'
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='project_memberships'
    )
    
    class Meta:
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['-created_at']

    ACTIVE_STATUSES = (Status.PLANNING, Status.IN_PROGRESS, Status.ON_HOLD)
    
    def __str__(self):
        return self.name
    
    @property
    def completion_percentage(self):
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        completed = self.tasks.filter(status=Task.Status.COMPLETED).count()
        return int((completed / total_tasks) * 100)


class Task(TimeStampedModel):
    """Tasks within a project."""
    
    class Status(models.TextChoices):
        TODO = 'todo', 'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        REVIEW = 'review', 'In Review'
        COMPLETED = 'completed', 'Completed'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tasks'
    )
    
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Estimated hours
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['status', '-priority', 'due_date']
    
    def __str__(self):
        return self.title


class ProjectDocument(TimeStampedModel):
    """Documents shared within a project."""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='project_documents/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Project Document'
        verbose_name_plural = 'Project Documents'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
