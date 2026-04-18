from django.db import models
from apps.core.models import TimeStampedModel


class ContactSubmission(TimeStampedModel):
    """Contact form submissions from the public website."""
    
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        READ = 'read', 'Read'
        REPLIED = 'replied', 'Replied'
        SPAM = 'spam', 'Spam'
    
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=300)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    
    # Tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Contact Submission'
        verbose_name_plural = 'Contact Submissions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"


class ServiceCategory(TimeStampedModel):
    """Categories for grouping services."""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Bootstrap icon class')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Service Category'
        verbose_name_plural = 'Service Categories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Service(TimeStampedModel):
    """Services offered by MTG - the service catalog."""
    
    class BillingType(models.TextChoices):
        HOURLY = 'hourly', 'Hourly Rate'
        FIXED = 'fixed', 'Fixed Price'
        MONTHLY = 'monthly', 'Monthly Retainer'
        PROJECT = 'project', 'Per Project'
    
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='services'
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    short_description = models.TextField(max_length=300)
    description = models.TextField()
    features = models.TextField(blank=True, help_text='One feature per line')
    icon = models.CharField(max_length=50, help_text='Bootstrap icon class (e.g., bi-cloud)')
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    
    # Pricing
    billing_type = models.CharField(max_length=100, default='hourly')
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_description = models.CharField(max_length=100, blank=True, help_text='e.g., "Starting at $150/hr"')
    
    # Display
    order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['order', 'title']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_featured']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def features_list(self):
        """Return features as a list."""
        if self.features:
            return [f.strip() for f in self.features.split('\n') if f.strip()]
        return []


class ServiceRequest(TimeStampedModel):
    """Client requests for services - leads from the website."""
    
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        REVIEWING = 'reviewing', 'Under Review'
        QUOTED = 'quoted', 'Quote Sent'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        CONVERTED = 'converted', 'Converted to Project'
    
    # Contact info
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    
    # Service details
    service = models.ForeignKey(
        Service, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='requests'
    )
    description = models.TextField(help_text='Describe your needs')
    budget_range = models.CharField(max_length=100, blank=True)
    timeline = models.CharField(max_length=100, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    assigned_to = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='service_requests'
    )
    
    # Tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True, help_text='How they found us')
    
    # Notes
    internal_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Service Request'
        verbose_name_plural = 'Service Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.service or 'General Inquiry'}"


class Testimonial(TimeStampedModel):
    """Client testimonials."""
    
    client_name = models.CharField(max_length=200)
    client_title = models.CharField(max_length=200, blank=True)
    client_company = models.CharField(max_length=200, blank=True)
    testimonial = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    photo = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'
        ordering = ['-is_featured', '-created_at']
    
    def __str__(self):
        return f"{self.client_name} - {self.client_company}"
