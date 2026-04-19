from django.contrib import admin
from .models import (
    Ticket, TicketComment, TicketAttachment,
    ConsultingProject, ProjectMilestone, Deliverable,
    ChangeRequest, ProjectNote, TimeEntry
)


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = ['created_at']


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ['file_size', 'created_at']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'subject', 'priority', 'status', 'category', 'created_by', 'assigned_to', 'is_overdue', 'created_at']
    list_filter = ['priority', 'status', 'category', 'created_at']
    search_fields = ['ticket_number', 'subject', 'description', 'created_by__email']
    date_hierarchy = 'created_at'
    readonly_fields = ['ticket_number', 'created_at', 'updated_at', 'first_response_at']
    inlines = [TicketCommentInline, TicketAttachmentInline]
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_number', 'subject', 'description')
        }),
        ('Classification', {
            'fields': ('priority', 'status', 'category')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_to', 'organization', 'contact', 'project')
        }),
        ('SLA & Tracking', {
            'fields': ('due_date', 'first_response_at'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at', 'closed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['content', 'ticket__ticket_number']


# ============ Consulting Project Admin ============

class ProjectMilestoneInline(admin.TabularInline):
    model = ProjectMilestone
    extra = 1
    ordering = ['order']


class DeliverableInline(admin.TabularInline):
    model = Deliverable
    extra = 0
    readonly_fields = ['submitted_at', 'approved_at', 'approved_by']


class ProjectNoteInline(admin.TabularInline):
    model = ProjectNote
    extra = 0
    readonly_fields = ['created_at']


@admin.register(ConsultingProject)
class ConsultingProjectAdmin(admin.ModelAdmin):
    list_display = ['project_number', 'name', 'organization', 'project_type', 'status', 'project_manager', 'start_date', 'target_end_date']
    list_filter = ['status', 'project_type', 'created_at']
    search_fields = ['project_number', 'name', 'organization__name']
    date_hierarchy = 'created_at'
    readonly_fields = ['project_number', 'created_at', 'updated_at']
    inlines = [ProjectMilestoneInline, DeliverableInline, ProjectNoteInline]
    filter_horizontal = ['team_members']
    
    fieldsets = (
        ('Project Information', {
            'fields': ('project_number', 'name', 'description', 'project_type', 'status')
        }),
        ('Client', {
            'fields': ('organization', 'primary_contact')
        }),
        ('Team', {
            'fields': ('project_manager', 'team_members')
        }),
        ('Timeline', {
            'fields': ('start_date', 'target_end_date', 'actual_end_date')
        }),
        ('Budget & Hours', {
            'fields': ('estimated_hours', 'actual_hours', 'budget')
        }),
        ('Intake', {
            'fields': ('intake_responses',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'milestone_type', 'status', 'sprint_number', 'due_date', 'story_points_planned', 'story_points_completed', 'order']
    list_filter = ['status', 'milestone_type', 'project']
    search_fields = ['name', 'project__name']


@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'milestone', 'status', 'due_date', 'approved_at']
    list_filter = ['status', 'project']
    search_fields = ['name', 'project__name']
    readonly_fields = ['submitted_at', 'approved_at', 'approved_by']


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'status', 'scope_impact', 'requested_by', 'created_at']
    list_filter = ['status', 'scope_impact']
    search_fields = ['title', 'project__name']
    readonly_fields = ['reviewed_at', 'created_at']
    
    fieldsets = (
        ('Request', {
            'fields': ('project', 'title', 'description', 'reason', 'requested_by')
        }),
        ('Impact Assessment', {
            'fields': ('scope_impact', 'budget_impact', 'schedule_impact_days')
        }),
        ('Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_notes')
        }),
    )


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'project', 'ticket', 'hours', 'billable', 'billed']
    list_filter = ['billable', 'billed', 'date', 'project']
    search_fields = ['description', 'project__name', 'user__email']
    date_hierarchy = 'date'
