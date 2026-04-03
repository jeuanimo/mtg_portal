from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class Organization(TimeStampedModel):
    """Client organizations/companies."""
    
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=50, blank=True, help_text='e.g., 1-10, 11-50, 51-200')
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='United States')
    
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['industry']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def primary_contact(self):
        return self.contacts.filter(is_primary=True).first()

    @property
    def address(self):
        """Compatibility helper for templates expecting a single address string."""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ]
        return ', '.join(part for part in parts if part)


class Contact(TimeStampedModel):
    """Individual contacts, potentially linked to organizations."""
    
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='contacts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='crm_contact'
    )
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    
    is_primary = models.BooleanField(default=False, help_text='Primary contact for organization')
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['organization', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Lead(TimeStampedModel):
    """Sales leads for potential clients."""
    
    class Status(models.TextChoices):
        NEW = 'new', 'New Lead'
        CONTACTED = 'contacted', 'Contacted'
        DISCOVERY = 'discovery', 'Discovery Scheduled'
        PROPOSAL = 'proposal', 'Proposal Sent'
        NEGOTIATION = 'negotiation', 'Negotiation'
        WON = 'won', 'Won'
        LOST = 'lost', 'Lost'
    
    class Source(models.TextChoices):
        WEBSITE = 'website', 'Website'
        REFERRAL = 'referral', 'Referral'
        COLD_CALL = 'cold_call', 'Cold Call'
        SOCIAL = 'social', 'Social Media'
        EVENT = 'event', 'Event'
        PARTNER = 'partner', 'Partner'
        OTHER = 'other', 'Other'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    # Basic info
    title = models.CharField(max_length=200, help_text='Lead title/description')
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name='leads'
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='leads'
    )
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WEBSITE)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    probability = models.PositiveSmallIntegerField(default=50, help_text='Win probability %')
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_leads'
    )
    
    # Dates
    expected_close_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    last_contacted = models.DateTimeField(null=True, blank=True)
    next_followup = models.DateTimeField(null=True, blank=True)
    
    # Conversion
    converted_to_client = models.BooleanField(default=False)
    converted_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    lost_reason = models.TextField(blank=True, help_text='Reason if lead was lost')
    
    class Meta:
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['expected_close_date']),
            models.Index(fields=['next_followup']),
            models.Index(fields=['priority', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.contact}"
    
    @property
    def weighted_value(self):
        if self.estimated_value and self.probability:
            return self.estimated_value * (self.probability / 100)
        return None
    
    @property
    def is_open(self):
        return self.status not in [self.Status.WON, self.Status.LOST]
    
    @property
    def days_in_pipeline(self):
        from django.utils import timezone
        return (timezone.now().date() - self.created_at.date()).days
    
    def convert_to_client(self, user=None):
        """Convert a won lead to a client account."""
        from django.utils import timezone
        
        if self.status != self.Status.WON:
            raise ValueError("Only won leads can be converted to clients")
        
        # Create user account for the contact if not exists
        if self.contact and not self.contact.user:
            from apps.accounts.models import User
            contact_user = User.objects.create(
                email=self.contact.email,
                first_name=self.contact.first_name,
                last_name=self.contact.last_name,
                phone=self.contact.phone or '',
                role=User.Role.CLIENT,
                organization=self.organization,
            )
            self.contact.user = contact_user
            self.contact.save()
        
        self.converted_to_client = True
        self.converted_at = timezone.now()
        self.save()
        
        return self.contact.user


class Activity(TimeStampedModel):
    """Activity log for leads and contacts."""
    
    class ActivityType(models.TextChoices):
        CALL = 'call', 'Phone Call'
        EMAIL = 'email', 'Email'
        MEETING = 'meeting', 'Meeting'
        NOTE = 'note', 'Note'
        STATUS_CHANGE = 'status_change', 'Status Change'
        TASK = 'task', 'Task Completed'
    
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE,
        null=True, blank=True, related_name='activities'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE,
        null=True, blank=True, related_name='activities'
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        null=True, blank=True, related_name='activities'
    )
    
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    subject = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='crm_activities'
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['lead', '-performed_at']),
            models.Index(fields=['contact', '-performed_at']),
        ]
    
    def __str__(self):
        return f"{self.activity_type}: {self.subject}"


class Task(TimeStampedModel):
    """Follow-up tasks for CRM items."""
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE,
        null=True, blank=True, related_name='tasks'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE,
        null=True, blank=True, related_name='tasks'
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        null=True, blank=True, related_name='tasks'
    )
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='crm_tasks'
    )
    
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['due_date', '-priority']
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['lead', 'status']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.due_date and self.status in [self.Status.PENDING, self.Status.IN_PROGRESS]:
            return timezone.now() > self.due_date
        return False
    
    def complete(self, user=None):
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save()
        
        # Log activity
        if self.lead:
            Activity.objects.create(
                lead=self.lead,
                activity_type=Activity.ActivityType.TASK,
                subject=f'Task completed: {self.title}',
                performed_by=user,
            )
