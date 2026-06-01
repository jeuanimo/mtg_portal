from django.contrib import admin
from .models import EmailDraft


@admin.register(EmailDraft)
class EmailDraftAdmin(admin.ModelAdmin):
    list_display = ('subject', 'to', 'created_by', 'updated_at')
    list_filter = ('created_by',)
    search_fields = ('subject', 'to', 'body')
