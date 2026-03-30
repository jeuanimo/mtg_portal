from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with email authentication and role-based permissions."""
    
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Administrator'
        FINANCE_ADMIN = 'finance_admin', 'Finance Administrator'
        CONSULTANT = 'consultant', 'Consultant'
        STAFF = 'staff', 'Staff Member'
        CLIENT = 'client', 'Client'
        PROSPECT = 'prospect', 'Prospect'
    
    username = None  # Remove username field
    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PROSPECT)
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    
    # Organization linkage for clients
    organization = models.ForeignKey(
        'crm.Organization', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='users'
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['organization']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_display_name(self):
        """Return full name or email if name not set."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email.split('@')[0]
    
    def get_dashboard_url(self):
        """Return appropriate dashboard URL based on role."""
        from django.urls import reverse
        if self.is_admin_user:
            return reverse('dashboard:index')
        elif self.is_finance_user:
            return reverse('invoicing:invoice_list')
        elif self.is_staff_user:
            return reverse('dashboard:index')
        else:
            return reverse('dashboard:index')
    
    # Role check properties
    @property
    def is_admin_user(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser
    
    @property
    def is_finance_user(self):
        return self.role in [self.Role.SUPER_ADMIN, self.Role.FINANCE_ADMIN] or self.is_superuser
    
    @property
    def is_staff_user(self):
        return self.role in [
            self.Role.SUPER_ADMIN, self.Role.FINANCE_ADMIN, 
            self.Role.CONSULTANT, self.Role.STAFF
        ] or self.is_staff
    
    @property
    def is_consultant(self):
        return self.role == self.Role.CONSULTANT or self.is_staff_user
    
    @property
    def is_client_user(self):
        return self.role == self.Role.CLIENT
    
    @property
    def is_prospect_user(self):
        return self.role == self.Role.PROSPECT
    
    # Permission checks
    def can_view_crm(self):
        return self.is_staff_user
    
    def can_view_finances(self):
        return self.is_finance_user
    
    def can_manage_users(self):
        return self.is_admin_user
    
    def can_view_all_tickets(self):
        return self.is_staff_user
    
    def can_view_all_projects(self):
        return self.is_staff_user
    
    @property
    def is_client(self):
        return self.role == self.Role.CLIENT


class UserProfile(models.Model):
    """Extended profile information for users."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='United States')
    timezone = models.CharField(max_length=50, default='America/Chicago')
    
    def __str__(self):
        return f"Profile for {self.user.email}"
