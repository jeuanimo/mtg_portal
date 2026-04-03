"""
Views for the tickets app.
"""
from urllib.parse import urlparse

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.decorators import staff_required
from .models import (
    Ticket, TicketAttachment,
    ConsultingProject, Deliverable,
    ChangeRequest, TimeEntry
)
from .forms import (
    TicketForm, TicketStaffForm, TicketCommentForm, TicketFilterForm, QuickTicketStatusForm,
    ConsultingProjectForm, ProjectIntakeForm, DeliverableForm, ChangeRequestForm, TimeEntryForm,
)

# URL name constants
TICKET_LIST_URL = 'tickets:ticket_list'
TICKET_DETAIL_URL = 'tickets:ticket_detail'
PROJECT_DETAIL_URL = 'tickets:project_detail'

# Message constants
ACCESS_DENIED_MSG = 'Access denied.'


def _apply_staff_ticket_filters(tickets, filter_form):
    """Apply filters for staff ticket list."""
    if not filter_form.is_valid():
        return tickets
    
    data = filter_form.cleaned_data
    if data.get('status'):
        tickets = tickets.filter(status=data['status'])
    if data.get('priority'):
        tickets = tickets.filter(priority=data['priority'])
    if data.get('category'):
        tickets = tickets.filter(category=data['category'])
    if data.get('assigned_to'):
        tickets = tickets.filter(assigned_to=data['assigned_to'])
    if data.get('search'):
        tickets = tickets.filter(
            Q(ticket_number__icontains=data['search']) |
            Q(subject__icontains=data['search'])
        )
    return tickets


def _get_client_tickets(user, status_filter=None):
    """Get tickets for a client user."""
    tickets = Ticket.objects.filter(
        Q(created_by=user) |
        Q(organization=user.organization)
    ).select_related('created_by', 'assigned_to')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    return tickets


def _get_ticket_form(request, is_post=False):
    """Get the appropriate ticket form based on user type."""
    if is_post:
        if request.user.is_staff_user:
            return TicketStaffForm(request.POST)
        return TicketForm(request.POST, user=request.user)
    if request.user.is_staff_user:
        return TicketStaffForm()
    return TicketForm(user=request.user)


def _handle_ticket_attachment(request, ticket):
    """Handle file attachment for a ticket."""
    if request.FILES.get('attachment'):
        TicketAttachment.objects.create(
            ticket=ticket,
            uploaded_by=request.user,
            file=request.FILES['attachment'],
        )


# ============ Ticket Views ============

@login_required
def ticket_dashboard(request):
    """Support ticket dashboard."""
    if request.user.is_staff_user:
        tickets = Ticket.objects.all()
    else:
        tickets = Ticket.objects.filter(
            Q(created_by=request.user) |
            Q(organization=request.user.organization)
        )
    
    # Stats
    open_count = tickets.filter(status__in=[Ticket.Status.NEW, Ticket.Status.IN_PROGRESS]).count()
    waiting_count = tickets.filter(status=Ticket.Status.WAITING).count()
    escalated_count = tickets.filter(status=Ticket.Status.ESCALATED).count()
    resolved_this_month = tickets.filter(
        resolved_at__month=timezone.now().month,
        resolved_at__year=timezone.now().year,
    ).count()
    
    recent_tickets = tickets.select_related('created_by', 'assigned_to')[:10]
    
    context = {
        'open_count': open_count,
        'waiting_count': waiting_count,
        'escalated_count': escalated_count,
        'resolved_this_month': resolved_this_month,
        'recent_tickets': recent_tickets,
    }
    return render(request, 'tickets/dashboard.html', context)


@login_required
def ticket_list(request):
    """List tickets - staff sees all, clients see their own."""
    if request.user.is_staff_user:
        tickets = Ticket.objects.select_related('created_by', 'assigned_to', 'organization').all()
        filter_form = TicketFilterForm(request.GET)
        tickets = _apply_staff_ticket_filters(tickets, filter_form)
    else:
        filter_form = None
        status_filter = request.GET.get('status')
        tickets = _get_client_tickets(request.user, status_filter)
    
    tickets = tickets.order_by('-created_at')
    
    paginator = Paginator(tickets, 20)
    page = request.GET.get('page')
    tickets = paginator.get_page(page)
    
    context = {
        'tickets': tickets,
        'filter_form': filter_form,
        'status_choices': Ticket.Status.choices,
        'priority_choices': Ticket.Priority.choices,
    }
    return render(request, 'tickets/ticket_list.html', context)


@login_required
def ticket_detail(request, pk):
    """Ticket detail view with comments."""
    ticket = get_object_or_404(
        Ticket.objects.select_related('created_by', 'assigned_to', 'organization', 'project'),
        pk=pk
    )
    
    # Check permission
    if not request.user.is_staff_user:
        if ticket.created_by != request.user and ticket.organization != request.user.organization:
            messages.error(request, 'You do not have access to this ticket.')
            return redirect(TICKET_LIST_URL)
    
    # Get comments (hide internal for clients)
    if request.user.is_staff_user:
        comments = ticket.comments.select_related('author').all()
    else:
        comments = ticket.comments.filter(is_internal=False).select_related('author')
    
    attachments = ticket.attachments.all()
    
    comment_form = TicketCommentForm(is_staff=request.user.is_staff_user)
    status_form = QuickTicketStatusForm(instance=ticket) if request.user.is_staff_user else None
    
    context = {
        'ticket': ticket,
        'comments': comments,
        'attachments': attachments,
        'comment_form': comment_form,
        'status_form': status_form,
    }
    return render(request, 'tickets/ticket_detail.html', context)


@login_required
def ticket_create(request):
    """Create a new support ticket."""
    if request.method == 'POST':
        form = _get_ticket_form(request, is_post=True)
        
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            if not request.user.is_staff_user and request.user.organization:
                ticket.organization = request.user.organization
            ticket.save()
            
            _handle_ticket_attachment(request, ticket)
            
            messages.success(request, f'Ticket #{ticket.ticket_number} created successfully.')
            return redirect(TICKET_DETAIL_URL, pk=ticket.pk)
    else:
        form = _get_ticket_form(request, is_post=False)
    
    context = {
        'form': form,
        'title': 'Submit New Ticket',
    }
    return render(request, 'tickets/ticket_form.html', context)


@login_required
@staff_required
def ticket_edit(request, pk):
    """Edit a ticket (staff only)."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        form = TicketStaffForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ticket updated.')
            return redirect(TICKET_DETAIL_URL, pk=pk)
    else:
        form = TicketStaffForm(instance=ticket)
    
    context = {
        'form': form,
        'ticket': ticket,
        'title': f'Edit Ticket #{ticket.ticket_number}',
    }
    return render(request, 'tickets/ticket_form.html', context)


@login_required
@require_POST
def ticket_add_comment(request, pk):
    """Add a comment to a ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Check permission
    if not request.user.is_staff_user:
        if ticket.created_by != request.user and ticket.organization != request.user.organization:
            messages.error(request, ACCESS_DENIED_MSG)
            return redirect(TICKET_LIST_URL)
    
    form = TicketCommentForm(request.POST, is_staff=request.user.is_staff_user)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.save()
        
        # Record first response for staff
        if request.user.is_staff_user and not comment.is_internal:
            ticket.record_first_response()
        
        messages.success(request, 'Comment added.')
    
    return redirect(TICKET_DETAIL_URL, pk=pk)


@login_required
@require_POST
def ticket_add_attachment(request, pk):
    """Add attachment to a ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.FILES.get('file'):
        TicketAttachment.objects.create(
            ticket=ticket,
            uploaded_by=request.user,
            file=request.FILES['file'],
        )
        messages.success(request, 'File uploaded.')
    
    return redirect(TICKET_DETAIL_URL, pk=pk)


@login_required
@require_POST
def ticket_update_status(request, pk):
    """Quick status update (staff only)."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if not request.user.is_staff_user:
        messages.error(request, ACCESS_DENIED_MSG)
        return redirect(TICKET_DETAIL_URL, pk=pk)
    
    form = QuickTicketStatusForm(request.POST, instance=ticket)
    if form.is_valid():
        form.save()
        messages.success(request, 'Ticket updated.')
    
    return redirect(TICKET_DETAIL_URL, pk=pk)


@login_required
@require_POST
def ticket_resolve(request, pk):
    """Mark ticket as resolved."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.user.is_staff_user or ticket.created_by == request.user:
        ticket.resolve()
        messages.success(request, 'Ticket resolved.')
    
    return redirect(TICKET_DETAIL_URL, pk=pk)


@login_required
@require_POST
def ticket_close(request, pk):
    """Close a ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.user.is_staff_user or ticket.created_by == request.user:
        ticket.close()
        messages.success(request, 'Ticket closed.')
    
    return redirect(TICKET_DETAIL_URL, pk=pk)


@login_required
@require_POST
def ticket_reopen(request, pk):
    """Reopen a resolved/closed ticket."""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.user.is_staff_user or ticket.created_by == request.user:
        ticket.reopen()
        messages.success(request, 'Ticket reopened.')
    
    return redirect(TICKET_DETAIL_URL, pk=pk)


# ============ Consulting Project Views ============

@login_required
@staff_required
def project_list(request):
    """List consulting projects."""
    projects = ConsultingProject.objects.select_related(
        'organization', 'project_manager'
    ).order_by('-created_at')
    
    status = request.GET.get('status')
    if status:
        projects = projects.filter(status=status)
    
    context = {
        'projects': projects,
        'status_choices': ConsultingProject.Status.choices,
    }
    return render(request, 'tickets/project_list.html', context)


@login_required
@staff_required
def project_create(request):
    """Create a new consulting project."""
    if request.method == 'POST':
        form = ConsultingProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'Project {project.project_number} created.')
            return redirect(PROJECT_DETAIL_URL, pk=project.pk)
    else:
        form = ConsultingProjectForm()
    
    context = {
        'form': form,
        'title': 'Create Project',
    }
    return render(request, 'tickets/project_form.html', context)


@login_required
def project_detail(request, pk):
    """Project detail view."""
    project = get_object_or_404(
        ConsultingProject.objects.select_related('organization', 'project_manager', 'primary_contact')
        .prefetch_related('milestones', 'deliverables', 'tickets', 'change_requests'),
        pk=pk
    )
    
    # Permission check for clients
    if not request.user.is_staff_user:
        if project.organization != request.user.organization:
            messages.error(request, ACCESS_DENIED_MSG)
            return redirect(TICKET_LIST_URL)
    
    context = {
        'project': project,
        'milestones': project.milestones.all(),
        'deliverables': project.deliverables.all(),
        'tickets': project.tickets.all()[:5],
        'change_requests': project.change_requests.all()[:5],
    }
    return render(request, 'tickets/project_detail.html', context)


@login_required
@staff_required
def project_edit(request, pk):
    """Edit a project."""
    project = get_object_or_404(ConsultingProject, pk=pk)
    
    if request.method == 'POST':
        form = ConsultingProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated.')
            return redirect(PROJECT_DETAIL_URL, pk=pk)
    else:
        form = ConsultingProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
        'title': f'Edit Project {project.project_number}',
    }
    return render(request, 'tickets/project_form.html', context)


@login_required
def project_intake(request, pk=None):
    """Project intake questionnaire."""
    project = get_object_or_404(ConsultingProject, pk=pk) if pk else None
    
    if request.method == 'POST':
        form = ProjectIntakeForm(request.POST)
        if form.is_valid():
            if project:
                project.intake_responses = form.cleaned_data
                project.save()
                messages.success(request, 'Intake form submitted.')
                return redirect(PROJECT_DETAIL_URL, pk=pk)
            else:
                # Create new project from intake
                messages.success(request, 'Thank you! We will be in touch shortly.')
                return redirect(TICKET_LIST_URL)
    else:
        initial = project.intake_responses if project else {}
        form = ProjectIntakeForm(initial=initial)
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'tickets/project_intake.html', context)


# ============ Deliverable Views ============

@login_required
def deliverable_detail(request, pk):
    """View deliverable details."""
    deliverable = get_object_or_404(
        Deliverable.objects.select_related('project', 'milestone', 'approved_by'),
        pk=pk
    )
    
    context = {
        'deliverable': deliverable,
    }
    return render(request, 'tickets/deliverable_detail.html', context)


@login_required
@staff_required
def deliverable_create(request, project_pk):
    """Create a new deliverable."""
    project = get_object_or_404(ConsultingProject, pk=project_pk)
    
    if request.method == 'POST':
        form = DeliverableForm(request.POST, request.FILES)
        if form.is_valid():
            deliverable = form.save(commit=False)
            deliverable.project = project
            deliverable.save()
            messages.success(request, 'Deliverable created.')
            return redirect(PROJECT_DETAIL_URL, pk=project_pk)
    else:
        form = DeliverableForm()
        form.fields['milestone'].queryset = project.milestones.all()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'tickets/deliverable_form.html', context)


@login_required
@require_POST
def deliverable_approve(request, pk):
    """Approve a deliverable."""
    deliverable = get_object_or_404(Deliverable, pk=pk)
    
    deliverable.status = Deliverable.Status.APPROVED
    deliverable.approved_at = timezone.now()
    deliverable.approved_by = request.user
    deliverable.feedback = request.POST.get('feedback', '')
    deliverable.save()
    
    messages.success(request, 'Deliverable approved.')
    return redirect('tickets:deliverable_detail', pk=pk)


# ============ Change Request Views ============

@login_required
def change_request_create(request, project_pk):
    """Submit a change request."""
    project = get_object_or_404(ConsultingProject, pk=project_pk)
    
    # Permission check
    if not request.user.is_staff_user:
        if project.organization != request.user.organization:
            messages.error(request, ACCESS_DENIED_MSG)
            return redirect(TICKET_LIST_URL)
    
    if request.method == 'POST':
        form = ChangeRequestForm(request.POST)
        if form.is_valid():
            cr = form.save(commit=False)
            cr.project = project
            cr.requested_by = request.user
            cr.save()
            messages.success(request, 'Change request submitted.')
            return redirect(PROJECT_DETAIL_URL, pk=project_pk)
    else:
        form = ChangeRequestForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'tickets/change_request_form.html', context)


@login_required
@staff_required
@require_POST
def change_request_review(request, pk):
    """Review a change request."""
    cr = get_object_or_404(ChangeRequest, pk=pk)
    
    action = request.POST.get('action')
    if action == 'approve':
        cr.status = ChangeRequest.Status.APPROVED
    elif action == 'reject':
        cr.status = ChangeRequest.Status.REJECTED
    
    cr.reviewed_by = request.user
    cr.reviewed_at = timezone.now()
    cr.review_notes = request.POST.get('notes', '')
    cr.save()
    
    messages.success(request, f'Change request {action}d.')
    return redirect(PROJECT_DETAIL_URL, pk=cr.project.pk)


# ============ Time Entry Views ============

@login_required
@staff_required
def time_entry_list(request):
    """List time entries."""
    entries = TimeEntry.objects.select_related('project', 'user', 'ticket').order_by('-date')
    
    # Filter by project
    project_id = request.GET.get('project')
    if project_id:
        entries = entries.filter(project_id=project_id)
    
    # Filter by user
    user_id = request.GET.get('user')
    if user_id:
        entries = entries.filter(user_id=user_id)
    
    context = {
        'entries': entries,
        'projects': ConsultingProject.objects.all(),
    }
    return render(request, 'tickets/time_entry_list.html', context)


@login_required
@staff_required
def time_entry_create(request):
    """Log time entry."""
    if request.method == 'POST':
        form = TimeEntryForm(request.POST, user=request.user)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            
            # Update project actual hours
            if entry.project:
                entry.project.actual_hours += entry.hours
                entry.project.save(update_fields=['actual_hours'])
            
            messages.success(request, 'Time logged.')
            
            # Return to where they came from (validate to prevent open redirect)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('tickets:time_entry_list')
    else:
        form = TimeEntryForm(user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'tickets/time_entry_form.html', context)
