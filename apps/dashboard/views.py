from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.crm.models import Lead, Contact, Organization
from apps.invoicing.models import Invoice, Payment
from apps.tickets.models import Ticket, ConsultingProject
from apps.projects.models import Project, Task
from apps.meetings.models import Meeting


@login_required
def index(request):
    """Main dashboard view - routes to role-specific dashboards."""
    user = request.user
    now = timezone.now()
    
    context = {
        'user': user,
        'page_title': 'Dashboard',
    }
    
    # Determine which dashboard to show based on role
    if user.is_superuser or user.role == 'admin':
        context.update(get_admin_dashboard_context(user, now))
        template = 'dashboard/admin_dashboard.html'
    elif user.role == 'finance':
        context.update(get_finance_dashboard_context(user, now))
        template = 'dashboard/finance_dashboard.html'
    elif user.role in ['consultant', 'support']:
        context.update(get_consultant_dashboard_context(user, now))
        template = 'dashboard/consultant_dashboard.html'
    elif user.is_staff:
        context.update(get_staff_dashboard_context(user, now))
        template = 'dashboard/staff_dashboard.html'
    else:
        # Client dashboard
        context.update(get_client_dashboard_context(user, now))
        template = 'dashboard/client_dashboard.html'
    
    return render(request, template, context)


def get_admin_dashboard_context(user, now):
    """Get dashboard context for admin/super users - full view."""
    thirty_days_ago = now - timedelta(days=30)
    
    # Lead stats
    leads_total = Lead.objects.count()
    leads_new = Lead.objects.filter(status='NEW').count()
    leads_qualified = Lead.objects.filter(status='QUALIFIED').count()
    leads_pipeline_value = Lead.objects.exclude(
        status__in=['WON', 'LOST']
    ).aggregate(total=Sum('estimated_value'))['total'] or 0
    
    # Pipeline stages for widget
    pipeline_stages = [
        {'name': 'New', 'count': leads_new},
        {'name': 'Qualified', 'count': leads_qualified},
        {'name': 'Proposal', 'count': Lead.objects.filter(status='PROPOSAL').count()},
        {'name': 'Negotiation', 'count': Lead.objects.filter(status='NEGOTIATION').count()},
    ]
    
    # Invoice stats
    invoices_outstanding = Invoice.objects.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    invoices_overdue = Invoice.objects.filter(status='OVERDUE').count()
    
    payments_this_month = Payment.objects.filter(
        status='COMPLETED',
        payment_date__gte=now.replace(day=1)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Ticket stats
    tickets_open = Ticket.objects.exclude(status__in=['RESOLVED', 'CLOSED']).count()
    tickets_urgent = Ticket.objects.filter(priority='URGENT').exclude(status__in=['RESOLVED', 'CLOSED']).count()
    tickets_high = Ticket.objects.filter(priority='HIGH').exclude(status__in=['RESOLVED', 'CLOSED']).count()
    
    # Meeting stats
    meetings_today = Meeting.objects.filter(
        scheduled_at__date=now.date(),
        status='SCHEDULED'
    ).count()
    
    # Recent items
    recent_leads = Lead.objects.select_related('contact', 'organization').order_by('-created_at')[:5]
    recent_tickets = Ticket.objects.select_related('created_by', 'organization').order_by('-created_at')[:5]
    open_tickets = Ticket.objects.exclude(status__in=['RESOLVED', 'CLOSED']).select_related('created_by', 'organization').order_by('-priority', '-created_at')[:5]
    
    invoices_due = Invoice.objects.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).select_related('organization', 'contact').order_by('due_date')[:5]
    
    # Upcoming meetings
    upcoming_meetings = Meeting.objects.filter(
        status='SCHEDULED',
        scheduled_at__gte=now
    ).select_related('organization', 'contact', 'host').order_by('scheduled_at')[:5]
    
    # Recent activity (combine different models)
    activities = []
    
    for lead in Lead.objects.order_by('-created_at')[:3]:
        activities.append({
            'type': 'lead',
            'title': f'New lead: {lead.title}',
            'description': lead.contact.full_name if lead.contact else '',
            'timestamp': lead.created_at,
        })
    
    for ticket in Ticket.objects.order_by('-created_at')[:3]:
        activities.append({
            'type': 'ticket',
            'title': f'Ticket #{ticket.ticket_number}',
            'description': ticket.subject[:50],
            'timestamp': ticket.created_at,
        })
    
    for payment in Payment.objects.filter(status='COMPLETED').order_by('-payment_date')[:2]:
        activities.append({
            'type': 'payment',
            'title': f'Payment received',
            'description': f'${payment.amount:.2f}',
            'timestamp': payment.payment_date,
        })
    
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return {
        'is_admin_dashboard': True,
        'leads_total': leads_total,
        'leads_new': leads_new,
        'leads_pipeline_value': leads_pipeline_value,
        'pipeline_stages': pipeline_stages,
        'invoices_outstanding': invoices_outstanding,
        'invoices_overdue': invoices_overdue,
        'payments_this_month': payments_this_month,
        'tickets_open': tickets_open,
        'tickets_urgent': tickets_urgent,
        'tickets_high': tickets_high,
        'meetings_today': meetings_today,
        'recent_leads': recent_leads,
        'recent_tickets': recent_tickets,
        'open_tickets': open_tickets,
        'invoices_due': invoices_due,
        'upcoming_meetings': upcoming_meetings,
        'recent_activities': activities[:8],
    }


def get_finance_dashboard_context(user, now):
    """Get dashboard context for finance role users."""
    thirty_days_ago = now - timedelta(days=30)
    
    # Invoice stats
    invoices_outstanding = Invoice.objects.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    invoices_overdue = Invoice.objects.filter(status='OVERDUE').count()
    invoices_overdue_value = Invoice.objects.filter(
        status='OVERDUE'
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    # Payment stats
    payments_this_month = Payment.objects.filter(
        status='COMPLETED',
        payment_date__gte=now.replace(day=1)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    payments_last_month = Payment.objects.filter(
        status='COMPLETED',
        payment_date__gte=(now.replace(day=1) - timedelta(days=1)).replace(day=1),
        payment_date__lt=now.replace(day=1)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Draft invoices
    draft_invoices = Invoice.objects.filter(status='DRAFT').count()
    
    # Recent payments
    recent_payments = Payment.objects.filter(
        status='COMPLETED'
    ).select_related('invoice__organization').order_by('-payment_date')[:10]
    
    # Invoices needing attention
    invoices_due = Invoice.objects.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).select_related('organization', 'contact').order_by('due_date')[:10]
    
    # Invoice aging
    aging_current = Invoice.objects.filter(
        status__in=['SENT', 'VIEWED'],
        due_date__gte=now.date()
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    aging_30 = Invoice.objects.filter(
        status='OVERDUE',
        due_date__gte=now.date() - timedelta(days=30),
        due_date__lt=now.date()
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    aging_60 = Invoice.objects.filter(
        status='OVERDUE',
        due_date__gte=now.date() - timedelta(days=60),
        due_date__lt=now.date() - timedelta(days=30)
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    aging_90plus = Invoice.objects.filter(
        status='OVERDUE',
        due_date__lt=now.date() - timedelta(days=60)
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    return {
        'is_finance_dashboard': True,
        'invoices_outstanding': invoices_outstanding,
        'invoices_overdue': invoices_overdue,
        'invoices_overdue_value': invoices_overdue_value,
        'payments_this_month': payments_this_month,
        'payments_last_month': payments_last_month,
        'draft_invoices': draft_invoices,
        'recent_payments': recent_payments,
        'invoices_due': invoices_due,
        'aging_current': aging_current,
        'aging_30': aging_30,
        'aging_60': aging_60,
        'aging_90plus': aging_90plus,
    }


def get_consultant_dashboard_context(user, now):
    """Get dashboard context for consultant/support users."""
    # Tickets assigned to user
    my_tickets = Ticket.objects.filter(assigned_to=user)
    tickets_open = my_tickets.exclude(status__in=['RESOLVED', 'CLOSED']).count()
    tickets_in_progress = my_tickets.filter(status='IN_PROGRESS').count()
    
    open_tickets = my_tickets.exclude(
        status__in=['RESOLVED', 'CLOSED']
    ).select_related('organization', 'created_by').order_by('-priority', '-created_at')[:10]
    
    # Consulting projects
    my_projects = ConsultingProject.objects.filter(
        Q(lead_consultant=user) | Q(team_members=user)
    ).distinct()
    
    active_projects = my_projects.filter(status__in=['PLANNING', 'IN_PROGRESS']).count()
    
    recent_projects = my_projects.select_related(
        'organization'
    ).order_by('-updated_at')[:5]
    
    # Time entries this week
    week_start = now - timedelta(days=now.weekday())
    from apps.tickets.models import TimeEntry
    time_this_week = TimeEntry.objects.filter(
        user=user,
        date__gte=week_start.date()
    ).aggregate(total=Sum('hours'))['total'] or 0
    
    # Upcoming meetings
    upcoming_meetings = Meeting.objects.filter(
        Q(host=user) | Q(attendees__user=user),
        status='SCHEDULED',
        scheduled_at__gte=now
    ).distinct().select_related('organization', 'contact').order_by('scheduled_at')[:5]
    
    # Meetings today
    meetings_today = Meeting.objects.filter(
        Q(host=user) | Q(attendees__user=user),
        scheduled_at__date=now.date(),
        status='SCHEDULED'
    ).distinct().count()
    
    return {
        'is_consultant_dashboard': True,
        'tickets_open': tickets_open,
        'tickets_in_progress': tickets_in_progress,
        'open_tickets': open_tickets,
        'active_projects': active_projects,
        'recent_projects': recent_projects,
        'time_this_week': time_this_week,
        'upcoming_meetings': upcoming_meetings,
        'meetings_today': meetings_today,
    }


def get_staff_dashboard_context(user, now):
    """Get dashboard context for general staff users."""
    # Similar to admin but more limited
    leads_new = Lead.objects.filter(status='NEW').count()
    leads_pipeline_value = Lead.objects.exclude(
        status__in=['WON', 'LOST']
    ).aggregate(total=Sum('estimated_value'))['total'] or 0
    
    tickets_open = Ticket.objects.exclude(status__in=['RESOLVED', 'CLOSED']).count()
    
    invoices_outstanding = Invoice.objects.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    recent_leads = Lead.objects.select_related('contact').order_by('-created_at')[:5]
    open_tickets = Ticket.objects.exclude(
        status__in=['RESOLVED', 'CLOSED']
    ).select_related('created_by', 'organization').order_by('-created_at')[:5]
    
    upcoming_meetings = Meeting.objects.filter(
        status='SCHEDULED',
        scheduled_at__gte=now
    ).select_related('organization', 'contact').order_by('scheduled_at')[:5]
    
    invoices_due = Invoice.objects.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).select_related('organization', 'contact').order_by('due_date')[:5]
    
    return {
        'is_staff_dashboard': True,
        'leads_new': leads_new,
        'leads_pipeline_value': leads_pipeline_value,
        'tickets_open': tickets_open,
        'invoices_outstanding': invoices_outstanding,
        'recent_leads': recent_leads,
        'open_tickets': open_tickets,
        'upcoming_meetings': upcoming_meetings,
        'invoices_due': invoices_due,
    }


def get_client_dashboard_context(user, now):
    """Get dashboard context for client users."""
    
    # Get user's tickets
    my_tickets = Ticket.objects.filter(created_by=user)
    tickets_open = my_tickets.exclude(status__in=['RESOLVED', 'CLOSED']).count()
    tickets_total = my_tickets.count()
    
    recent_tickets = my_tickets.order_by('-created_at')[:5]
    
    # Get invoices (where user is contact or connected to organization)
    my_invoices = Invoice.objects.filter(
        Q(contact__user=user) |
        Q(organization__contacts__user=user)
    ).distinct()
    
    invoices_unpaid = my_invoices.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).count()
    
    balance_due = my_invoices.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).aggregate(total=Sum('balance_due'))['total'] or 0
    
    invoices_due = my_invoices.filter(
        status__in=['SENT', 'VIEWED', 'PARTIAL', 'OVERDUE']
    ).order_by('due_date')[:5]
    
    # Get projects
    my_projects = Project.objects.filter(
        Q(team_members=user) |
        Q(organization__contacts__user=user)
    ).distinct()
    active_projects = my_projects.filter(status='IN_PROGRESS').count()
    
    # Tasks assigned to user
    my_tasks = Task.objects.filter(assigned_to=user).exclude(status='COMPLETED')[:5]
    
    # Upcoming meetings
    upcoming_meetings = Meeting.objects.filter(
        Q(attendees__user=user) | Q(contact__user=user),
        status='SCHEDULED',
        scheduled_at__gte=now
    ).distinct().select_related('organization', 'host').order_by('scheduled_at')[:5]
    
    return {
        'is_client_dashboard': True,
        'tickets_open': tickets_open,
        'tickets_total': tickets_total,
        'recent_tickets': recent_tickets,
        'invoices_unpaid': invoices_unpaid,
        'balance_due': balance_due,
        'invoices_due': invoices_due,
        'active_projects': active_projects,
        'my_tasks': my_tasks,
        'upcoming_meetings': upcoming_meetings,
    }


@login_required
def reports(request):
    """Reports page for staff."""
    if not request.user.is_staff:
        return render(request, 'dashboard/access_denied.html')
    
    # Generate report data
    now = timezone.now()
    
    # Monthly revenue
    monthly_payments = []
    for i in range(6):
        month_start = (now - timedelta(days=30*i)).replace(day=1)
        if i == 0:
            month_end = now
        else:
            month_end = (now - timedelta(days=30*(i-1))).replace(day=1)
        
        total = Payment.objects.filter(
            status='completed',
            payment_date__gte=month_start,
            payment_date__lt=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_payments.append({
            'month': month_start.strftime('%B %Y'),
            'total': total
        })
    
    # Lead conversion rate
    total_leads = Lead.objects.count()
    won_leads = Lead.objects.filter(status='won').count()
    conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
    
    context = {
        'monthly_payments': list(reversed(monthly_payments)),
        'total_leads': total_leads,
        'won_leads': won_leads,
        'conversion_rate': round(conversion_rate, 1),
    }
    return render(request, 'dashboard/reports.html', context)
