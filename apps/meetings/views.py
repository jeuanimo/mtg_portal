from urllib.parse import urlparse

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.html import escape
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator

# Trusted domains for video meeting URLs
TRUSTED_MEETING_DOMAINS = frozenset({
    'zoom.us', 'us02web.zoom.us', 'us04web.zoom.us', 'us05web.zoom.us', 'us06web.zoom.us',
    'meet.google.com', 'teams.microsoft.com', 'teams.live.com',
    'webex.com', 'meetingsamer.webex.com', 'meetingsemea.webex.com',
    'gotomeeting.com', 'global.gotomeeting.com',
})


def _is_trusted_meeting_url(url):
    """Validate that a meeting URL is from a trusted video conferencing domain."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        # Check if host matches or is a subdomain of a trusted domain
        return any(
            host == domain or host.endswith('.' + domain)
            for domain in TRUSTED_MEETING_DOMAINS
        )
    except (ValueError, AttributeError):
        return False

from .models import Meeting, MeetingAttendee, MeetingRecording, AvailabilitySlot
from .forms import (
    MeetingForm, QuickMeetingForm, MeetingNotesForm,
    MeetingAttendeeForm, AvailabilitySlotForm, MeetingFilterForm
)
from .services import video_service

# URL name constants
MEETING_DETAIL_URL = 'meetings:meeting_detail'
MEETING_LIST_URL = 'meetings:meeting_list'


def _meeting_access_q(user):
    """Return the visibility scope for meeting querysets."""
    if user.is_staff_user:
        return Q()
    return Q(organizer=user) | Q(host=user) | Q(participants=user)


@login_required
def meeting_dashboard(request):
    """Dashboard view for meetings."""
    now = timezone.now()
    user = request.user
    
    # Upcoming meetings (next 7 days)
    upcoming_meetings = Meeting.objects.filter(
        _meeting_access_q(user),
        start_time__gte=now,
        start_time__lte=now + timezone.timedelta(days=7),
        status__in=Meeting.UPCOMING_STATUSES,
    ).distinct().order_by('start_time')[:10]
    
    # Today's meetings
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)
    todays_meetings = Meeting.objects.filter(
        _meeting_access_q(user),
        start_time__gte=today_start,
        start_time__lt=today_end
    ).distinct().order_by('start_time')
    
    # Recent past meetings
    past_meetings = Meeting.objects.filter(
        _meeting_access_q(user),
        end_time__lt=now,
        status=Meeting.Status.COMPLETED,
    ).distinct().order_by('-start_time')[:5]
    
    # Stats
    stats = {
        'total_upcoming': Meeting.objects.filter(
            _meeting_access_q(user),
            start_time__gte=now,
            status__in=Meeting.UPCOMING_STATUSES,
        ).distinct().count(),
        'this_week': Meeting.objects.filter(
            _meeting_access_q(user),
            start_time__gte=now,
            start_time__lt=now + timezone.timedelta(days=7)
        ).distinct().count(),
        'pending_notes': Meeting.objects.filter(
            Q(organizer=user) | Q(host=user),
            status=Meeting.Status.COMPLETED,
            notes=''
        ).count(),
    }
    
    context = {
        'upcoming_meetings': upcoming_meetings,
        'todays_meetings': todays_meetings,
        'past_meetings': past_meetings,
        'stats': stats,
    }
    return render(request, 'meetings/dashboard.html', context)


@login_required
def meeting_list(request):
    """List all meetings with filters."""
    filter_form = MeetingFilterForm(request.GET)
    user = request.user
    
    # Base queryset
    if user.is_staff_user:
        meetings = Meeting.objects.all()
    else:
        meetings = Meeting.objects.filter(
            _meeting_access_q(user)
        ).distinct()
    
    # Apply filters
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('status'):
            meetings = meetings.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data.get('meeting_type'):
            meetings = meetings.filter(meeting_type=filter_form.cleaned_data['meeting_type'])
        if filter_form.cleaned_data.get('from_date'):
            meetings = meetings.filter(start_time__date__gte=filter_form.cleaned_data['from_date'])
        if filter_form.cleaned_data.get('to_date'):
            meetings = meetings.filter(start_time__date__lte=filter_form.cleaned_data['to_date'])
        if filter_form.cleaned_data.get('search'):
            search = filter_form.cleaned_data['search']
            meetings = meetings.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(organization__name__icontains=search)
            )
    
    meetings = meetings.select_related('organizer', 'host', 'organization').order_by('-start_time')
    
    # Pagination
    paginator = Paginator(meetings, 20)
    page = request.GET.get('page', 1)
    meetings = paginator.get_page(page)
    
    context = {
        'meetings': meetings,
        'filter_form': filter_form,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': meetings,
    }
    return render(request, 'meetings/meeting_list.html', context)


@login_required
def meeting_create(request):
    """Create a new meeting."""
    if request.method == 'POST':
        form = MeetingForm(request.POST, user=request.user)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.organizer = request.user
            meeting.save()
            form.save_m2m()
            
            # Create video meeting if provider is configured
            video_service.create_meeting(meeting)
            
            messages.success(request, f"Meeting '{meeting.title}' scheduled successfully.")
            return redirect(MEETING_DETAIL_URL, pk=meeting.pk)
    else:
        form = MeetingForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'meetings/meeting_form.html', context)


@login_required
def meeting_detail(request, pk):
    """View meeting details."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    # Check access
    user = request.user
    if not user.is_staff_user:
        if not (meeting.organizer == user or meeting.host == user or user in meeting.participants.all()):
            raise Http404("Meeting not found")
    
    attendees = meeting.attendees.select_related('user', 'contact').all()
    recordings = meeting.recordings.all()
    
    # Forms for adding notes and attendees
    notes_form = MeetingNotesForm(instance=meeting)
    attendee_form = MeetingAttendeeForm(meeting=meeting)
    
    context = {
        'meeting': meeting,
        'attendees': attendees,
        'recordings': recordings,
        'notes_form': notes_form,
        'attendee_form': attendee_form,
        'can_edit': meeting.organizer == user or meeting.host == user or user.is_staff_user,
    }
    return render(request, 'meetings/meeting_detail.html', context)


@login_required
def meeting_edit(request, pk):
    """Edit a meeting."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    # Check permission
    if not (meeting.organizer == request.user or meeting.host == request.user or request.user.is_staff_user):
        messages.error(request, "You don't have permission to edit this meeting.")
        return redirect(MEETING_DETAIL_URL, pk=pk)
    
    if request.method == 'POST':
        form = MeetingForm(request.POST, instance=meeting, user=request.user)
        if form.is_valid():
            meeting = form.save()
            # Update video meeting
            video_service.update_meeting(meeting)
            messages.success(request, "Meeting updated successfully.")
            return redirect(MEETING_DETAIL_URL, pk=meeting.pk)
    else:
        form = MeetingForm(instance=meeting, user=request.user)
    
    context = {'form': form, 'meeting': meeting}
    return render(request, 'meetings/meeting_form.html', context)


@login_required
@require_POST
def meeting_cancel(request, pk):
    """Cancel a meeting."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    if not (meeting.organizer == request.user or meeting.host == request.user or request.user.is_staff_user):
        messages.error(request, "You don't have permission to cancel this meeting.")
        return redirect(MEETING_DETAIL_URL, pk=pk)
    
    reason = request.POST.get('reason', '')
    meeting.cancel_meeting(reason)
    video_service.delete_meeting(meeting)
    
    messages.success(request, "Meeting cancelled.")
    return redirect(MEETING_LIST_URL)


@login_required
@require_POST
def meeting_start(request, pk):
    """Mark meeting as in progress."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    if not (meeting.host == request.user or meeting.organizer == request.user or request.user.is_staff_user):
        messages.error(request, "Only the host can start this meeting.")
        return redirect(MEETING_DETAIL_URL, pk=pk)
    
    meeting.start_meeting()
    messages.success(request, "Meeting started.")
    
    # Redirect to meeting URL if available (validated against trusted domains)
    # nosec: URL is validated by _is_trusted_meeting_url before redirect
    validated_url = None
    if meeting.host_url and _is_trusted_meeting_url(meeting.host_url):
        validated_url = meeting.host_url  # noqa: S310
    elif meeting.meeting_url and _is_trusted_meeting_url(meeting.meeting_url):
        validated_url = meeting.meeting_url  # noqa: S310
    
    if validated_url:
        return redirect(validated_url)
    
    return redirect(MEETING_DETAIL_URL, pk=pk)


@login_required
@require_POST
def meeting_complete(request, pk):
    """Mark meeting as completed."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    if not (meeting.host == request.user or meeting.organizer == request.user or request.user.is_staff_user):
        messages.error(request, "Only the host can complete this meeting.")
        return redirect(MEETING_DETAIL_URL, pk=pk)
    
    meeting.complete_meeting()
    messages.success(request, "Meeting marked as completed. Don't forget to add notes!")
    return redirect(MEETING_DETAIL_URL, pk=pk)


@login_required
@require_POST
def meeting_update_notes(request, pk):
    """Update meeting notes."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    if not (meeting.host == request.user or meeting.organizer == request.user or request.user.is_staff_user):
        messages.error(request, "You don't have permission to update meeting notes.")
        return redirect(MEETING_DETAIL_URL, pk=pk)
    
    form = MeetingNotesForm(request.POST, instance=meeting)
    if form.is_valid():
        form.save()
        messages.success(request, "Meeting notes saved.")
    
    return redirect(MEETING_DETAIL_URL, pk=pk)


@login_required
@require_POST
def meeting_add_attendee(request, pk):
    """Add an attendee to a meeting."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    if not (meeting.organizer == request.user or meeting.host == request.user or request.user.is_staff_user):
        messages.error(request, "You don't have permission to add attendees.")
        return redirect(MEETING_DETAIL_URL, pk=pk)
    
    form = MeetingAttendeeForm(request.POST, meeting=meeting)
    if form.is_valid():
        form.save()
        messages.success(request, "Attendee added.")
    else:
        for error in form.errors.values():
            messages.error(request, error)
    
    return redirect(MEETING_DETAIL_URL, pk=pk)


@login_required
@require_POST
def meeting_remove_attendee(request, pk, attendee_pk):
    """Remove an attendee from a meeting."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    if not (meeting.organizer == request.user or meeting.host == request.user or request.user.is_staff_user):
        messages.error(request, "You don't have permission to remove attendees.")
        return redirect(MEETING_DETAIL_URL, pk=pk)
    
    attendee = get_object_or_404(MeetingAttendee, pk=attendee_pk, meeting=meeting)
    attendee.delete()
    messages.success(request, "Attendee removed.")
    
    return redirect(MEETING_DETAIL_URL, pk=pk)


def client_join(request, token):
    """Client meeting join page (public)."""
    meeting = get_object_or_404(Meeting, client_join_token=token)
    
    if not meeting.allow_client_join:
        raise Http404("This meeting link is not valid")
    
    context = {
        'meeting': meeting,
        'can_join': meeting.can_join,
    }
    return render(request, 'meetings/client_join.html', context)


@login_required
def quick_schedule(request):
    """Quick meeting scheduling."""
    if request.method == 'POST':
        form = QuickMeetingForm(request.POST)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.organizer = request.user
            meeting.host = request.user
            meeting.save()
            
            video_service.create_meeting(meeting)
            
            messages.success(request, "Meeting scheduled successfully.")
            return redirect(MEETING_DETAIL_URL, pk=meeting.pk)
    else:
        form = QuickMeetingForm()
    
    context = {'form': form}
    return render(request, 'meetings/quick_schedule.html', context)


@login_required
def meeting_calendar(request):
    """Calendar view of meetings."""
    user = request.user
    
    # Get meetings for calendar (JSON endpoint for AJAX)
    if request.GET.get('format') == 'json':
        start = request.GET.get('start')
        end = request.GET.get('end')
        
        meetings = Meeting.objects.filter(
            _meeting_access_q(user)
        )
        
        if start:
            meetings = meetings.filter(start_time__gte=start)
        if end:
            meetings = meetings.filter(end_time__lte=end)
        
        events = []
        for meeting in meetings.distinct():
            events.append({
                'id': meeting.pk,
                'title': meeting.title,
                'start': meeting.start_time.isoformat(),
                'end': meeting.end_time.isoformat(),
                'url': f'/meetings/{meeting.pk}/',
                'color': {
                    'SCHEDULED': '#6c757d',
                    'CONFIRMED': '#0d6efd',
                    'IN_PROGRESS': '#198754',
                    'COMPLETED': '#20c997',
                    'CANCELLED': '#dc3545',
                    'NO_SHOW': '#ffc107',
                }.get(meeting.status, '#6c757d'),
            })
        
        return JsonResponse(events, safe=False)
    
    return render(request, 'meetings/calendar.html')


# ============ Availability Management ============

@login_required
def availability_list(request):
    """Manage availability slots."""
    slots = AvailabilitySlot.objects.filter(user=request.user).order_by('day_of_week', 'start_time')
    
    if request.method == 'POST':
        form = AvailabilitySlotForm(request.POST)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.user = request.user
            slot.save()
            messages.success(request, "Availability slot added.")
            return redirect('meetings:availability_list')
    else:
        form = AvailabilitySlotForm()
    
    context = {
        'slots': slots,
        'form': form,
    }
    return render(request, 'meetings/availability_list.html', context)


@login_required
@require_POST
def availability_delete(request, pk):
    """Delete availability slot."""
    slot = get_object_or_404(AvailabilitySlot, pk=pk, user=request.user)
    slot.delete()
    messages.success(request, "Availability slot removed.")
    return redirect('meetings:availability_list')


# ============ Recordings ============

@login_required
def recording_list(request):
    """List meeting recordings."""
    user = request.user
    
    if user.is_staff_user:
        recordings = MeetingRecording.objects.all()
    else:
        recordings = MeetingRecording.objects.filter(
            Q(meeting__organizer=user) | Q(meeting__host=user) | Q(meeting__participants=user)
        ).distinct()
    
    recordings = recordings.select_related('meeting').order_by('-created_at')
    
    paginator = Paginator(recordings, 20)
    page = request.GET.get('page', 1)
    recordings = paginator.get_page(page)
    
    context = {
        'recordings': recordings,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': recordings,
    }
    return render(request, 'meetings/recording_list.html', context)


@login_required
@require_POST
def sync_recordings(request, pk):
    """Sync recordings from video provider."""
    meeting = get_object_or_404(Meeting, pk=pk)
    
    if not request.user.is_staff_user:
        messages.error(request, "Only staff can sync recordings.")
        return redirect(MEETING_DETAIL_URL, pk=pk)
    
    recordings = video_service.sync_recordings(meeting)
    messages.success(request, f"Synced {len(recordings)} recording(s).")
    return redirect(MEETING_DETAIL_URL, pk=pk)


# ============ HTMX Endpoints ============

@login_required
def get_organization_contacts(request):
    """HTMX endpoint to get contacts for an organization."""
    org_id = request.GET.get('organization')
    
    from apps.crm.models import Contact
    contacts = Contact.objects.filter(organization_id=org_id).order_by('last_name', 'first_name')
    
    options = '<option value="">Select contact...</option>'
    for contact in contacts:
        options += f'<option value="{contact.pk}">{escape(contact.full_name)}</option>'

    return JsonResponse({'html': options})
