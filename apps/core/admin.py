from django.contrib import admin
from apps.core.widgets import DatalistTextInput
from .models import SiteSettings, Notification, Document


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'contact_email', 'contact_phone']
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['created_at', 'read_at', 'email_sent_at']
    date_hierarchy = 'created_at'


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'document_type', 'uploaded_by', 'file_size', 'is_client_visible', 'created_at']
    list_filter = ['document_type', 'is_client_visible', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['file_size', 'created_at', 'updated_at']

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'document_type':
            kwargs['widget'] = DatalistTextInput(choices=Document.DocumentType.choices)
        return super().formfield_for_dbfield(db_field, request, **kwargs)
