from django.contrib import admin
from .models import ContactSubmission, ServiceCategory, Service, ServiceRequest, Testimonial


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['ip_address', 'user_agent', 'created_at']
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_spam', 'mark_as_replied']
    
    def mark_as_spam(self, request, queryset):
        queryset.update(status=ContactSubmission.Status.SPAM)
    mark_as_spam.short_description = "Mark selected as spam"
    
    def mark_as_replied(self, request, queryset):
        queryset.update(status=ContactSubmission.Status.REPLIED)
    mark_as_replied.short_description = "Mark selected as replied"


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'billing_type', 'base_price', 'is_featured', 'is_active', 'order']
    list_filter = ['category', 'billing_type', 'is_featured', 'is_active']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['order', 'is_featured', 'is_active']


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'service', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'service', 'assigned_to', 'created_at']
    search_fields = ['name', 'email', 'company', 'description']
    readonly_fields = ['ip_address', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'client_company', 'rating', 'is_featured', 'is_active']
    list_filter = ['is_featured', 'is_active', 'rating']
    search_fields = ['client_name', 'client_company', 'testimonial']
    list_editable = ['is_featured', 'is_active']
