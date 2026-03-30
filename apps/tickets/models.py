from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.crm.models import Organization, Contact


class Ticket(TimeStampedModel):
    """Support tickets."""
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        IN_PROGRESS = 'in_progress', 'In Progress'
        WAITING = 'waiting', 'Waiting on Client'
        ESCALATED = 'escalated', 'Escalated'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'
    
    class Category(models.TextChoices):
        TECHNICAL = 'technical', 'Technical Support'
        BILLING = 'billing', 'Billing'
        GENERAL = 'general', 'General Inquiry'
        BUG = 'bug', 'Bug Report'
        FEATURE = 'feature', 'Feature Request'
        SECURITY = 'security', 'Security Issue'
        HARDWARE = 'hardware', 'Hardware Support'
        SOFTWARE = 'software', 'Software Support'
        NETWORK = 'network', 'Network Issue'
    
    # Ticket info
    ticket_number = models.CharField(max_length=20, unique=True)
    subject = models.CharField(max_length=300)
    description = models.TextField()
    
    # Classification
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    
    # Relationships
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tickets'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tickets'
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tickets'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tickets'
    )
    
    # SLA and tracking
    due_date = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Related to project/consulting
    project = models.ForeignKey(
        'ConsultingProject', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tickets'
    )
    
    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['priority', 'status']),
        ]
    
    def __str__(self):
        return f"#{self.ticket_number}: {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            last = Ticket.objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.ticket_number = f"TKT-{next_num:05d}"
        super().save(*args, **kwargs)
    
    @property
    def is_open(self):
        return self.status not in [self.Status.RESOLVED, self.Status.CLOSED]
    
    @property
    def is_overdue(self):
        if self.due_date and self.is_open:
            return timezone.now() > self.due_date
        return False
    
    def record_first_response(self):
        """Record the time of first staff response."""
        if not self.first_response_at:
            self.first_response_at = timezone.now()
            self.save(update_fields=['first_response_at'])
    
    def resolve(self):
        """Mark ticket as resolved."""
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])
    
    def close(self):
        """Close the ticket."""
        self.status = self.Status.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at'])
    
    def reopen(self):
        """Reopen a resolved/closed ticket."""
        self.status = self.Status.IN_PROGRESS
        self.resolved_at = None
        self.closed_at = None
        self.save(update_fields=['status', 'resolved_at', 'closed_at'])


class TicketComment(TimeStampedModel):
    """Comments/replies on tickets."""
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    is_internal = models.BooleanField(default=False, help_text='Internal notes not visible to client')
    
    class Meta:
        verbose_name = 'Ticket Comment'
        verbose_name_plural = 'Ticket Comments'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author} on {self.ticket}"


class TicketAttachment(TimeStampedModel):
    """File attachments for tickets."""
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='ticket_attachments/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Ticket Attachment'
        verbose_name_plural = 'Ticket Attachments'
    
    def __str__(self):
        return self.filename
    
    def save(self, *args, **kwargs):
        if self.file:
            self.filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class ConsultingProject(TimeStampedModel):
    """Consulting/development projects."""
    
    class Status(models.TextChoices):
        INTAKE = 'intake', 'Intake'
        DISCOVERY = 'discovery', 'Discovery'
        PROPOSAL = 'proposal', 'Proposal'
        IN_PROGRESS = 'in_progress', 'In Progress'
        ON_HOLD = 'on_hold', 'On Hold'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class ProjectType(models.TextChoices):
        CONSULTING = 'consulting', 'IT Consulting'
        DEVELOPMENT = 'development', 'Software Development'
        IMPLEMENTATION = 'implementation', 'System Implementation'
        MIGRATION = 'migration', 'Migration/Upgrade'
        ASSESSMENT = 'assessment', 'Security Assessment'
        TRAINING = 'training', 'Training'
        SUPPORT = 'support', 'Managed Support'
        OTHER = 'other', 'Other'
    
    # Basic info
    name = models.CharField(max_length=200)
    project_number = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    
    # Type and status
    project_type = models.CharField(max_length=20, choices=ProjectType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INTAKE)
    
    # Client
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='projects'
    )
    primary_contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    # Team
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_projects'
    )
    team_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='project_assignments'
    )
    
    # Timeline
    start_date = models.DateField(null=True, blank=True)
    target_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Budget
    estimated_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Intake questionnaire responses (JSON)
    intake_responses = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Consulting Project'
        verbose_name_plural = 'Consulting Projects'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project_number}: {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.project_number:
            last = ConsultingProject.objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.project_number = f"PRJ-{next_num:04d}"
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        return self.status in [self.Status.DISCOVERY, self.Status.IN_PROGRESS]
    
    @property
    def hours_remaining(self):
        if self.estimated_hours:
            return self.estimated_hours - self.actual_hours
        return None


class ProjectMilestone(TimeStampedModel):
    """Milestones for project tracking."""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        BLOCKED = 'blocked', 'Blocked'
    
    project = models.ForeignKey(
        ConsultingProject, on_delete=models.CASCADE, related_name='milestones'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Project Milestone'
        verbose_name_plural = 'Project Milestones'
        ordering = ['order', 'due_date']
    
    def __str__(self):
        return self.name


class Deliverable(TimeStampedModel):
    """Project deliverables."""
    
    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        IN_REVIEW = 'in_review', 'In Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
    
    project = models.ForeignKey(
        ConsultingProject, on_delete=models.CASCADE, related_name='deliverables'
    )
    milestone = models.ForeignKey(
        ProjectMilestone, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    
    due_date = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # File attachment
    file = models.FileField(upload_to='deliverables/', blank=True)
    
    # Approval
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_deliverables'
    )
    feedback = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Deliverable'
        verbose_name_plural = 'Deliverables'
        ordering = ['due_date']
    
    def __str__(self):
        return self.name


class ChangeRequest(TimeStampedModel):
    """Change requests for projects."""
    
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        IMPLEMENTED = 'implemented', 'Implemented'
    
    class Impact(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
    
    project = models.ForeignKey(
        ConsultingProject, on_delete=models.CASCADE, related_name='change_requests'
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    reason = models.TextField(help_text='Business justification for the change')
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    
    # Impact assessment
    scope_impact = models.CharField(max_length=20, choices=Impact.choices, default=Impact.MEDIUM)
    budget_impact = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    schedule_impact_days = models.IntegerField(null=True, blank=True)
    
    # Tracking
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_changes'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_changes'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Change Request'
        verbose_name_plural = 'Change Requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"CR: {self.title}"


class ProjectNote(TimeStampedModel):
    """Internal notes for projects."""
    
    project = models.ForeignKey(
        ConsultingProject, on_delete=models.CASCADE, related_name='notes'
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    
    class Meta:
        verbose_name = 'Project Note'
        verbose_name_plural = 'Project Notes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note by {self.author} on {self.project}"


class TimeEntry(TimeStampedModel):
    """Time tracking entries."""
    
    project = models.ForeignKey(
        ConsultingProject, on_delete=models.CASCADE, related_name='time_entries'
    )
    ticket = models.ForeignKey(
        Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='time_entries'
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField()
    
    billable = models.BooleanField(default=True)
    billed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Time Entry'
        verbose_name_plural = 'Time Entries'
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.hours}h by {self.user} on {self.date}"
