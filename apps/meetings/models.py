from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import TimeStampedModel
import uuid


class Meeting(TimeStampedModel):
    """Scheduled meetings."""
    
    class MeetingType(models.TextChoices):
        VIDEO = 'VIDEO', 'Video Call'
        PHONE = 'PHONE', 'Phone Call'
        IN_PERSON = 'IN_PERSON', 'In Person'
        DEMO = 'DEMO', 'Product Demo'
        CONSULTING = 'CONSULTING', 'Consulting Session'
        SUPPORT = 'SUPPORT', 'Support Call'
        PROJECT_REVIEW = 'PROJECT_REVIEW', 'Project Review'
    
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        NO_SHOW = 'NO_SHOW', 'No Show'
        RESCHEDULED = 'RESCHEDULED', 'Rescheduled'
    
    class Provider(models.TextChoices):
        ZOOM = 'ZOOM', 'Zoom'
        GOOGLE_MEET = 'GOOGLE_MEET', 'Google Meet'
        TEAMS = 'TEAMS', 'Microsoft Teams'
        OTHER = 'OTHER', 'Other'
        NONE = 'NONE', 'None (Phone/In-Person)'
    
    # Unique meeting identifier
    meeting_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    meeting_type = models.CharField(max_length=20, choices=MeetingType.choices, default=MeetingType.VIDEO)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    
    # Scheduling
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    timezone = models.CharField(max_length=50, default='America/Chicago')
    
    # Organizer and participants
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_meetings'
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hosted_meetings', help_text='Meeting host (may differ from organizer)'
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='meeting_invitations'
    )
    
    # External attendees (clients)
    organization = models.ForeignKey(
        'crm.Organization', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='meetings'
    )
    contact = models.ForeignKey(
        'crm.Contact', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='meetings'
    )
    
    # Video meeting details
    video_provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.ZOOM)
    meeting_url = models.URLField(blank=True, help_text='Join URL for participants')
    host_url = models.URLField(blank=True, help_text='Host start URL')
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_password = models.CharField(max_length=50, blank=True)
    external_meeting_id = models.CharField(max_length=200, blank=True, help_text='ID from video provider')
    
    # Location (for in-person)
    location = models.CharField(max_length=300, blank=True)
    
    # Notes and agenda
    agenda = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text='Meeting notes/minutes')
    action_items = models.TextField(blank=True, help_text='Follow-up action items')
    
    # Related objects
    project = models.ForeignKey(
        'tickets.ConsultingProject', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='meetings'
    )
    ticket = models.ForeignKey(
        'tickets.Ticket', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='meetings'
    )
    
    # Reminders
    reminder_sent = models.BooleanField(default=False)
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)
    
    # Recording
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True)
    recording_password = models.CharField(max_length=50, blank=True)
    
    # Client access
    client_join_token = models.UUIDField(default=uuid.uuid4, editable=False)
    allow_client_join = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Meeting'
        verbose_name_plural = 'Meetings'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['start_time', 'status']),
            models.Index(fields=['organizer', 'status']),
            models.Index(fields=['meeting_uuid']),
            models.Index(fields=['client_join_token']),
        ]

    UPCOMING_STATUSES = (Status.SCHEDULED, Status.CONFIRMED)
    ACTIVE_STATUSES = (Status.SCHEDULED, Status.CONFIRMED, Status.IN_PROGRESS)
    
    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def scheduled_at(self):
        """Backwards-compatible alias for legacy templates."""
        return self.start_time

    @property
    def duration_minutes(self):
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0

    @property
    def duration(self):
        """Backwards-compatible alias for legacy templates."""
        return self.duration_minutes
    
    @property
    def is_upcoming(self):
        return self.start_time > timezone.now() and self.status in self.UPCOMING_STATUSES
    
    @property
    def is_past(self):
        return self.end_time < timezone.now()
    
    @property
    def can_join(self):
        """Check if meeting can be joined (15 min before to end time)"""
        now = timezone.now()
        start_buffer = self.start_time - timezone.timedelta(minutes=15)
        return start_buffer <= now <= self.end_time and self.status in self.ACTIVE_STATUSES
    
    def start_meeting(self):
        self.status = self.Status.IN_PROGRESS
        self.save(update_fields=['status', 'updated_at'])
    
    def complete_meeting(self):
        self.status = self.Status.COMPLETED
        self.save(update_fields=['status', 'updated_at'])
    
    def cancel_meeting(self, reason=''):
        self.status = self.Status.CANCELLED
        if reason:
            self.notes = f"Cancelled: {reason}\n\n{self.notes}"
        self.save(update_fields=['status', 'notes', 'updated_at'])
    
    def get_client_join_url(self):
        from django.urls import reverse
        return reverse('meetings:client_join', kwargs={'token': self.client_join_token})


class MeetingAttendee(TimeStampedModel):
    """Track meeting attendance."""
    
    class RSVPStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'
        TENTATIVE = 'TENTATIVE', 'Tentative'
    
    class AttendanceStatus(models.TextChoices):
        NOT_YET = 'NOT_YET', 'Not Yet'
        ATTENDED = 'ATTENDED', 'Attended'
        NO_SHOW = 'NO_SHOW', 'No Show'
        PARTIAL = 'PARTIAL', 'Partial'
    
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='attendees')
    
    # Either internal user or external contact
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name='meeting_attendances'
    )
    contact = models.ForeignKey(
        'crm.Contact', on_delete=models.CASCADE, null=True, blank=True,
        related_name='meeting_attendances'
    )
    
    # For ad-hoc external attendees
    email = models.EmailField(blank=True)
    name = models.CharField(max_length=200, blank=True)
    
    rsvp_status = models.CharField(max_length=20, choices=RSVPStatus.choices, default=RSVPStatus.PENDING)
    attendance_status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.NOT_YET)
    
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    
    # Invitation
    invitation_sent = models.BooleanField(default=False)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Meeting Attendee'
        verbose_name_plural = 'Meeting Attendees'
        unique_together = [
            ('meeting', 'user'),
            ('meeting', 'contact'),
            ('meeting', 'email'),
        ]
    
    def __str__(self):
        attendee_name = self.get_display_name()
        return f"{attendee_name} - {self.meeting.title}"
    
    def get_display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.email
        elif self.contact:
            return self.contact.full_name
        elif self.name:
            return self.name
        return self.email


class MeetingRecording(TimeStampedModel):
    """Meeting recordings."""
    
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='recordings')
    
    title = models.CharField(max_length=200)
    recording_url = models.URLField()
    password = models.CharField(max_length=50, blank=True)
    
    duration_seconds = models.PositiveIntegerField(default=0)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    
    # Transcript
    transcript = models.TextField(blank=True)
    transcript_url = models.URLField(blank=True)
    
    # External provider data
    external_id = models.CharField(max_length=200, blank=True)
    
    class Meta:
        verbose_name = 'Meeting Recording'
        verbose_name_plural = 'Meeting Recordings'
    
    def __str__(self):
        return f"Recording: {self.meeting.title}"


class AvailabilitySlot(TimeStampedModel):
    """Available time slots for scheduling."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='availability_slots'
    )
    
    # Recurring availability
    day_of_week = models.PositiveSmallIntegerField(
        choices=[
            (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
            (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')
        ]
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Availability Slot'
        verbose_name_plural = 'Availability Slots'
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return f"{self.user.email} - {days[self.day_of_week]} {self.start_time}-{self.end_time}"
