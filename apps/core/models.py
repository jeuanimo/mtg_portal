from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class SiteSettings(models.Model):
    """Site-wide settings (singleton model)."""
    site_name = models.CharField(max_length=200, default='Mitchell Technology Group')
    tagline = models.CharField(max_length=500, blank=True)
    contact_email = models.EmailField(default='contact@mitchelltechgroup.com')
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Social links
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    
    # SEO
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)
    
    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'
    
    def __str__(self):
        return self.site_name
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Notification(TimeStampedModel):
    """User notifications for various system events."""
    
    class NotificationType(models.TextChoices):
        INFO = 'info', 'Information'
        SUCCESS = 'success', 'Success'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'
        TICKET = 'ticket', 'Ticket Update'
        INVOICE = 'invoice', 'Invoice'
        PROJECT = 'project', 'Project Update'
        MEETING = 'meeting', 'Meeting Reminder'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.INFO)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, help_text='URL to relevant item')
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Email notification tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email}: {self.title}"
    
    def mark_as_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class Document(TimeStampedModel):
    """General document storage - can be linked to various models."""
    
    class DocumentType(models.TextChoices):
        CONTRACT = 'contract', 'Contract'
        PROPOSAL = 'proposal', 'Proposal'
        INVOICE = 'invoice', 'Invoice'
        REPORT = 'report', 'Report'
        SPECIFICATION = 'specification', 'Specification'
        OTHER = 'other', 'Other'
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    file = models.FileField(upload_to='documents/%Y/%m/')
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Owner and access
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='uploaded_documents'
    )
    
    # Related objects (polymorphic linking)
    # Using GenericForeignKey would be more elegant but this is simpler
    organization_id = models.PositiveIntegerField(null=True, blank=True)
    project_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Access control
    is_client_visible = models.BooleanField(default=True, help_text='Can clients see this document?')
    
    class Meta:
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_type', '-created_at']),
            models.Index(fields=['organization_id']),
            models.Index(fields=['project_id']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
