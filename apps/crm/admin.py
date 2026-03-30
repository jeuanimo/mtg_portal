from django.contrib import admin
from .models import Organization, Contact, Lead, Activity, Task


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    readonly_fields = ['performed_by', 'performed_at']


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ['title', 'assigned_to', 'priority', 'status', 'due_date']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'city', 'state', 'created_at']
    list_filter = ['industry', 'state', 'created_at']
    search_fields = ['name', 'email', 'city']
    inlines = [ContactInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'organization', 'job_title', 'is_primary']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'organization__name']
    list_select_related = ['organization']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['title', 'contact', 'status', 'priority', 'source', 'estimated_value', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'source', 'assigned_to', 'converted_to_client', 'created_at']
    search_fields = ['title', 'contact__first_name', 'contact__last_name', 'organization__name']
    list_select_related = ['contact', 'organization', 'assigned_to']
    date_hierarchy = 'created_at'
    inlines = [ActivityInline, TaskInline]
    
    fieldsets = (
        ('Lead Information', {
            'fields': ('title', 'contact', 'organization', 'status', 'source', 'priority')
        }),
        ('Value & Probability', {
            'fields': ('estimated_value', 'probability', 'expected_close_date')
        }),
        ('Assignment & Follow-up', {
            'fields': ('assigned_to', 'next_followup', 'last_contacted')
        }),
        ('Conversion', {
            'fields': ('converted_to_client', 'converted_at', 'closed_date', 'lost_reason'),
            'classes': ('collapse',),
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    readonly_fields = ['converted_at', 'last_contacted']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['subject', 'activity_type', 'lead', 'contact', 'performed_by', 'performed_at']
    list_filter = ['activity_type', 'performed_at']
    search_fields = ['subject', 'description']
    list_select_related = ['lead', 'contact', 'performed_by']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'lead', 'contact', 'assigned_to', 'priority', 'status', 'due_date', 'is_overdue']
    list_filter = ['status', 'priority', 'assigned_to', 'due_date']
    search_fields = ['title', 'description', 'lead__title', 'contact__email']
    list_select_related = ['lead', 'contact', 'organization', 'assigned_to']
    date_hierarchy = 'due_date'
    
    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
