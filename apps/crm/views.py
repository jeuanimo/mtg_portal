import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.accounts.decorators import staff_required
from .models import Organization, Contact, Lead, Activity, Task
from .forms import OrganizationForm, ContactForm, LeadForm, ActivityForm, TaskForm

logger = logging.getLogger(__name__)

# URL name constants
LEAD_DETAIL_URL = 'crm:lead_detail'
CONTACT_DETAIL_URL = 'crm:contact_detail'
ORGANIZATION_DETAIL_URL = 'crm:organization_detail'
TASK_LIST_URL = 'crm:task_list'


@login_required
@staff_required
def lead_list(request):
    """List all leads with filtering."""
    leads = Lead.objects.select_related('contact', 'organization', 'assigned_to').all()
    
    # Filtering
    status = request.GET.get('status')
    if status:
        leads = leads.filter(status=status)
    
    source = request.GET.get('source')
    if source:
        leads = leads.filter(source=source)
    
    assigned = request.GET.get('assigned_to')
    if assigned == 'me':
        leads = leads.filter(assigned_to=request.user)
    
    search = request.GET.get('q')
    if search:
        leads = leads.filter(
            Q(title__icontains=search) |
            Q(contact__first_name__icontains=search) |
            Q(contact__last_name__icontains=search) |
            Q(organization__name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(leads, 20)
    page = request.GET.get('page')
    leads = paginator.get_page(page)
    
    # Stats
    stats = {
        'total': Lead.objects.count(),
        'new': Lead.objects.filter(status='new').count(),
        'pipeline_value': Lead.objects.exclude(status__in=['won', 'lost']).aggregate(
            total=Sum('estimated_value')
        )['total'] or 0,
        'won_this_month': Lead.objects.filter(
            status='won',
            closed_date__month=timezone.now().month
        ).count(),
    }
    
    context = {
        'leads': leads,
        'stats': stats,
        'status_choices': Lead.Status.choices,
        'source_choices': Lead.Source.choices,
    }
    return render(request, 'crm/lead_list.html', context)


@login_required
@staff_required
def pipeline_view(request):
    """Kanban-style pipeline view for leads."""
    stages = ['new', 'contacted', 'discovery', 'proposal', 'negotiation']
    
    pipeline = {}
    for stage in stages:
        pipeline[stage] = Lead.objects.filter(status=stage).select_related(
            'contact', 'organization', 'assigned_to'
        ).order_by('-priority', '-created_at')
    
    # Stats
    stats = {
        'total_value': Lead.objects.exclude(status__in=['won', 'lost']).aggregate(
            total=Sum('estimated_value')
        )['total'] or 0,
        'weighted_value': sum(
            lead.weighted_value or 0 
            for lead in Lead.objects.exclude(status__in=['won', 'lost'])
        ),
        'won_count': Lead.objects.filter(status='won').count(),
        'lost_count': Lead.objects.filter(status='lost').count(),
    }
    
    context = {
        'pipeline': pipeline,
        'stats': stats,
        'stages': Lead.Status.choices[:5],  # Exclude won/lost
    }
    return render(request, 'crm/pipeline.html', context)


@login_required
@staff_required
def lead_detail(request, pk):
    """Lead detail view."""
    lead = get_object_or_404(Lead.objects.select_related('contact', 'organization', 'assigned_to'), pk=pk)
    activities = lead.activities.select_related('performed_by').all()[:10]
    tasks = lead.tasks.select_related('assigned_to').all()
    
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.lead = lead
            activity.performed_by = request.user
            activity.save()
            
            # Update last contacted
            if activity.activity_type in ['call', 'email', 'meeting']:
                lead.last_contacted = timezone.now()
                lead.save()
            
            messages.success(request, 'Activity added.')
            return redirect(LEAD_DETAIL_URL, pk=pk)
    else:
        form = ActivityForm()
    
    context = {
        'lead': lead,
        'activities': activities,
        'tasks': tasks,
        'activity_form': form,
    }
    return render(request, 'crm/lead_detail.html', context)


@login_required
@staff_required
def lead_create(request):
    """Create a new lead."""
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save()
            messages.success(request, f'Lead "{lead.title}" created.')
            return redirect(LEAD_DETAIL_URL, pk=lead.pk)
    else:
        form = LeadForm()
    
    return render(request, 'crm/lead_form.html', {'form': form, 'action': 'Create'})


@login_required
@staff_required
def lead_edit(request, pk):
    """Edit an existing lead."""
    lead = get_object_or_404(Lead, pk=pk)
    old_status = lead.status
    
    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            lead = form.save()
            
            # Log status change if applicable
            if lead.status != old_status:
                Activity.objects.create(
                    lead=lead,
                    activity_type=Activity.ActivityType.STATUS_CHANGE,
                    subject=f'Status changed from {old_status} to {lead.status}',
                    performed_by=request.user,
                )
            
            messages.success(request, 'Lead updated.')
            return redirect(LEAD_DETAIL_URL, pk=pk)
    else:
        form = LeadForm(instance=lead)
    
    return render(request, 'crm/lead_form.html', {'form': form, 'lead': lead, 'action': 'Edit'})


@login_required
@staff_required
def lead_update_status(request, pk):
    """Quick status update for a lead."""
    lead = get_object_or_404(Lead, pk=pk)
    old_status = lead.status
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Lead.Status.choices):
            lead.status = new_status
            
            if new_status in ['won', 'lost']:
                lead.closed_date = timezone.now().date()
            
            if new_status == 'lost':
                lead.lost_reason = request.POST.get('lost_reason', '')
            
            lead.save()
            
            # Log activity
            Activity.objects.create(
                lead=lead,
                activity_type=Activity.ActivityType.STATUS_CHANGE,
                subject=f'Status changed from {old_status} to {new_status}',
                performed_by=request.user,
            )
            
            messages.success(request, f'Lead status updated to {lead.get_status_display()}')
    
    return redirect(LEAD_DETAIL_URL, pk=pk)


@login_required
@staff_required
def lead_convert(request, pk):
    """Convert a won lead to a client account."""
    lead = get_object_or_404(Lead, pk=pk)
    
    if lead.status != Lead.Status.WON:
        messages.error(request, 'Only won leads can be converted to clients.')
        return redirect(LEAD_DETAIL_URL, pk=pk)
    
    if lead.converted_to_client:
        messages.warning(request, 'This lead has already been converted.')
        return redirect(LEAD_DETAIL_URL, pk=pk)
    
    try:
        client_user = lead.convert_to_client(user=request.user)
        messages.success(
            request, 
            f'Lead converted! Client account created for {client_user.email}'
        )
    except Exception as e:
        logger.error('Lead conversion failed for lead #%s: %s', pk, e)
        messages.error(request, 'An error occurred converting this lead. Please try again or contact support.')
    
    return redirect(LEAD_DETAIL_URL, pk=pk)


@login_required
@staff_required
def contact_list(request):
    """List all contacts."""
    contacts = Contact.objects.select_related('organization').all()
    
    search = request.GET.get('q')
    if search:
        contacts = contacts.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(organization__name__icontains=search)
        )
    
    paginator = Paginator(contacts, 20)
    page = request.GET.get('page')
    contacts = paginator.get_page(page)
    
    return render(request, 'crm/contact_list.html', {'contacts': contacts})


@login_required
@staff_required
def contact_detail(request, pk):
    """Contact detail view."""
    contact = get_object_or_404(Contact.objects.select_related('organization'), pk=pk)
    leads = contact.leads.all()
    activities = contact.activities.select_related('performed_by').all()[:10]
    tasks = contact.tasks.select_related('assigned_to').all()
    
    context = {
        'contact': contact,
        'leads': leads,
        'activities': activities,
        'tasks': tasks,
    }
    return render(request, 'crm/contact_detail.html', context)


@login_required
@staff_required
def contact_create(request):
    """Create a new contact."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            messages.success(request, f'Contact "{contact.full_name}" created.')
            return redirect(CONTACT_DETAIL_URL, pk=contact.pk)
    else:
        form = ContactForm()
    
    return render(request, 'crm/contact_form.html', {'form': form, 'action': 'Create'})


@login_required
@staff_required
def contact_edit(request, pk):
    """Edit an existing contact."""
    contact = get_object_or_404(Contact, pk=pk)
    
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contact updated.')
            return redirect(CONTACT_DETAIL_URL, pk=pk)
    else:
        form = ContactForm(instance=contact)
    
    return render(request, 'crm/contact_form.html', {'form': form, 'contact': contact, 'action': 'Edit'})


@login_required
@staff_required
def organization_list(request):
    """List all organizations."""
    organizations = Organization.objects.annotate(contact_count=Count('contacts')).order_by('name')
    
    search = request.GET.get('q')
    if search:
        organizations = organizations.filter(name__icontains=search)
    
    paginator = Paginator(organizations, 20)
    page = request.GET.get('page')
    organizations = paginator.get_page(page)
    
    return render(request, 'crm/organization_list.html', {'organizations': organizations})


@login_required
@staff_required
def organization_detail(request, pk):
    """Organization detail view."""
    organization = get_object_or_404(Organization, pk=pk)
    contacts = organization.contacts.all()
    leads = organization.leads.all()
    tasks = organization.tasks.select_related('assigned_to').all()
    
    context = {
        'organization': organization,
        'contacts': contacts,
        'leads': leads,
        'tasks': tasks,
    }
    return render(request, 'crm/organization_detail.html', context)


@login_required
@staff_required
def organization_create(request):
    """Create a new organization."""
    if request.method == 'POST':
        form = OrganizationForm(request.POST)
        if form.is_valid():
            org = form.save()
            messages.success(request, f'Organization "{org.name}" created.')
            return redirect(ORGANIZATION_DETAIL_URL, pk=org.pk)
    else:
        form = OrganizationForm()
    
    return render(request, 'crm/organization_form.html', {'form': form, 'action': 'Create'})


@login_required
@staff_required
def organization_edit(request, pk):
    """Edit an existing organization."""
    organization = get_object_or_404(Organization, pk=pk)
    
    if request.method == 'POST':
        form = OrganizationForm(request.POST, instance=organization)
        if form.is_valid():
            form.save()
            messages.success(request, 'Organization updated.')
            return redirect(ORGANIZATION_DETAIL_URL, pk=pk)
    else:
        form = OrganizationForm(instance=organization)
    
    return render(request, 'crm/organization_form.html', {'form': form, 'organization': organization, 'action': 'Edit'})


# Task Views
@login_required
@staff_required
def task_list(request):
    """List all tasks with filtering."""
    tasks = Task.objects.select_related('lead', 'contact', 'assigned_to').all()
    
    # Filters
    status = request.GET.get('status')
    if status:
        tasks = tasks.filter(status=status)
    
    assigned = request.GET.get('assigned_to')
    if assigned == 'me':
        tasks = tasks.filter(assigned_to=request.user)
    
    priority = request.GET.get('priority')
    if priority:
        tasks = tasks.filter(priority=priority)
    
    # Overdue filter
    if request.GET.get('overdue'):
        tasks = tasks.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        )
    
    paginator = Paginator(tasks, 20)
    page = request.GET.get('page')
    tasks = paginator.get_page(page)
    
    # Stats
    stats = {
        'pending': Task.objects.filter(status='pending').count(),
        'overdue': Task.objects.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        ).count(),
        'completed_today': Task.objects.filter(
            status='completed',
            completed_at__date=timezone.now().date()
        ).count(),
    }
    
    context = {
        'tasks': tasks,
        'stats': stats,
        'status_choices': Task.Status.choices,
        'priority_choices': Task.Priority.choices,
    }
    return render(request, 'crm/task_list.html', context)


@login_required
@staff_required
def task_create(request):
    """Create a new task."""
    lead_id = request.GET.get('lead')
    contact_id = request.GET.get('contact')
    
    kwargs = {}
    if lead_id:
        kwargs['lead'] = get_object_or_404(Lead, pk=lead_id)
    if contact_id:
        kwargs['contact'] = get_object_or_404(Contact, pk=contact_id)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, **kwargs)
        if form.is_valid():
            task = form.save()
            messages.success(request, f'Task "{task.title}" created.')
            
            # Redirect to source if applicable
            if task.lead:
                return redirect(LEAD_DETAIL_URL, pk=task.lead.pk)
            if task.contact:
                return redirect(CONTACT_DETAIL_URL, pk=task.contact.pk)
            return redirect(TASK_LIST_URL)
    else:
        form = TaskForm(**kwargs)
        form.fields['assigned_to'].initial = request.user
    
    return render(request, 'crm/task_form.html', {'form': form, 'action': 'Create'})


@login_required
@staff_required
def task_edit(request, pk):
    """Edit a task."""
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated.')
            return redirect(TASK_LIST_URL)
    else:
        form = TaskForm(instance=task)
    
    return render(request, 'crm/task_form.html', {'form': form, 'task': task, 'action': 'Edit'})


@login_required
@staff_required
def task_complete(request, pk):
    """Mark a task as complete."""
    task = get_object_or_404(Task, pk=pk)
    task.complete(user=request.user)
    messages.success(request, f'Task "{task.title}" completed.')
    
    # Return to source
    if task.lead:
        return redirect(LEAD_DETAIL_URL, pk=task.lead.pk)
    if task.contact:
        return redirect(CONTACT_DETAIL_URL, pk=task.contact.pk)
    return redirect(TASK_LIST_URL)


# CRM Dashboard
@login_required
@staff_required
def crm_dashboard(request):
    """CRM metrics dashboard."""
    today = timezone.now().date()
    this_month = today.replace(day=1)
    
    # Leads stats
    lead_stats = {
        'total': Lead.objects.count(),
        'new_this_month': Lead.objects.filter(created_at__gte=this_month).count(),
        'won_this_month': Lead.objects.filter(status='won', closed_date__gte=this_month).count(),
        'lost_this_month': Lead.objects.filter(status='lost', closed_date__gte=this_month).count(),
        'pipeline_value': Lead.objects.exclude(status__in=['won', 'lost']).aggregate(
            total=Sum('estimated_value')
        )['total'] or 0,
    }
    
    # Tasks stats
    task_stats = {
        'pending': Task.objects.filter(status='pending').count(),
        'overdue': Task.objects.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        ).count(),
        'due_today': Task.objects.filter(
            due_date__date=today,
            status__in=['pending', 'in_progress']
        ).count(),
    }
    
    # Recent leads
    recent_leads = Lead.objects.select_related('contact', 'assigned_to').order_by('-created_at')[:5]
    
    # My tasks
    my_tasks = Task.objects.filter(
        assigned_to=request.user,
        status__in=['pending', 'in_progress']
    ).order_by('due_date')[:5]
    
    # Leads by status (for chart)
    leads_by_status = Lead.objects.values('status').annotate(count=Count('id'))
    
    context = {
        'lead_stats': lead_stats,
        'task_stats': task_stats,
        'recent_leads': recent_leads,
        'my_tasks': my_tasks,
        'leads_by_status': list(leads_by_status),
    }
    return render(request, 'crm/dashboard.html', context)
