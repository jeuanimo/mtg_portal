from django.contrib import admin
from .models import Meeting, MeetingAttendee, MeetingRecording, AvailabilitySlot


class MeetingAttendeeInline(admin.TabularInline):
    model = MeetingAttendee
    extra = 0
    readonly_fields = ['joined_at', 'left_at', 'invitation_sent_at']


class MeetingRecordingInline(admin.TabularInline):
    model = MeetingRecording
    extra = 0
    readonly_fields = ['duration_seconds', 'file_size_bytes']


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['title', 'meeting_type', 'status', 'organizer', 'host', 'organization', 'start_time', 'video_provider']
    list_filter = ['meeting_type', 'status', 'video_provider', 'start_time']
    search_fields = ['title', 'description', 'organizer__email', 'organization__name']
    filter_horizontal = ['participants']
    date_hierarchy = 'start_time'
    readonly_fields = ['meeting_uuid', 'client_join_token', 'created_at', 'updated_at']
    inlines = [MeetingAttendeeInline, MeetingRecordingInline]
    
    fieldsets = (
        ('Meeting Details', {
            'fields': ('title', 'description', 'meeting_type', 'status')
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time', 'timezone')
        }),
        ('Participants', {
            'fields': ('organizer', 'host', 'participants', 'organization', 'contact')
        }),
        ('Video Conference', {
            'fields': ('video_provider', 'meeting_url', 'host_url', 'meeting_id', 'meeting_password', 'external_meeting_id'),
            'classes': ('collapse',)
        }),
        ('Location', {
            'fields': ('location',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('agenda', 'notes', 'action_items')
        }),
        ('Related Items', {
            'fields': ('project', 'ticket'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_recorded', 'allow_client_join', 'recording_url', 'recording_password'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('meeting_uuid', 'client_join_token', 'reminder_sent', 'reminder_24h_sent', 'reminder_1h_sent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MeetingAttendee)
class MeetingAttendeeAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'get_attendee_name', 'rsvp_status', 'attendance_status', 'invitation_sent']
    list_filter = ['rsvp_status', 'attendance_status', 'invitation_sent']
    search_fields = ['meeting__title', 'user__email', 'contact__first_name', 'email']
    
    def get_attendee_name(self, obj):
        return obj.get_display_name()
    get_attendee_name.short_description = 'Attendee'


@admin.register(MeetingRecording)
class MeetingRecordingAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'title', 'duration_seconds', 'created_at']
    search_fields = ['meeting__title', 'title']
    readonly_fields = ['external_id', 'created_at']


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ['user', 'day_of_week', 'start_time', 'end_time', 'is_active']
    list_filter = ['is_active', 'day_of_week']
    search_fields = ['user__email']
