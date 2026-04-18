"""
Views for the invoicing app.
"""
import logging
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from apps.accounts.decorators import finance_required
from apps.crm.models import Contact
from .models import Invoice, InvoiceItem, Payment, RecurringInvoice
from .forms import (
    InvoiceForm, InvoiceItemFormSet, QuickInvoiceForm,
    PaymentForm, RecurringInvoiceForm, RecurringInvoiceItemFormSet,
    InvoiceEmailForm, InvoiceFilterForm,
)
from .services import StripeService, process_webhook_event

logger = logging.getLogger(__name__)

# URL name constants
INVOICE_DETAIL_URL = 'invoicing:invoice_detail'
INVOICE_LIST_URL = 'invoicing:invoice_list'
INVOICE_EDIT_URL = 'invoicing:invoice_edit'
RECURRING_LIST_URL = 'invoicing:recurring_list'

# HTML constants
SELECT_CONTACT_OPTION = '<option value="">Select a contact</option>'


def _apply_invoice_filters(invoices, filter_form):
    """Apply filter form values to invoice queryset."""
    if not filter_form.is_valid():
        return invoices
    
    data = filter_form.cleaned_data
    if data.get('status'):
        invoices = invoices.filter(status=data['status'])
    if data.get('organization'):
        invoices = invoices.filter(organization=data['organization'])
    if data.get('date_from'):
        invoices = invoices.filter(issue_date__gte=data['date_from'])
    if data.get('date_to'):
        invoices = invoices.filter(issue_date__lte=data['date_to'])
    if data.get('search'):
        invoices = invoices.filter(invoice_number__icontains=data['search'])
    return invoices


def _get_client_invoices(user):
    """Get invoices visible to a client user."""
    return Invoice.objects.filter(
        Q(organization__contacts__user=user) |
        Q(contact__user=user)
    ).select_related('organization', 'contact').distinct()


@login_required
@finance_required
def invoice_dashboard(request):
    """Dashboard for invoicing overview."""
    today = date.today()
    
    # Get summary stats
    invoices = Invoice.objects.all()
    
    draft_count = invoices.filter(status=Invoice.Status.DRAFT).count()
    sent_count = invoices.filter(status=Invoice.Status.SENT).count()
    overdue_count = invoices.filter(
        status=Invoice.Status.SENT,
        due_date__lt=today
    ).count()
    
    # Revenue this month
    this_month_start = today.replace(day=1)
    paid_this_month = invoices.filter(
        status__in=[Invoice.Status.PAID, Invoice.Status.PARTIAL],
        paid_date__gte=this_month_start,
    ).aggregate(total=Sum('total'))['total'] or 0

    # Outstanding balance
    outstanding = invoices.filter(
        status__in=[Invoice.Status.SENT, Invoice.Status.PARTIAL]
    ).aggregate(total=Sum('balance_due'))
    outstanding_total = (outstanding['total'] or 0)
    
    # Recent invoices
    recent_invoices = invoices.select_related('organization').order_by('-created_at')[:10]
    
    context = {
        'draft_count': draft_count,
        'sent_count': sent_count,
        'overdue_count': overdue_count,
        'paid_this_month': paid_this_month,
        'outstanding_total': outstanding_total,
        'recent_invoices': recent_invoices,
    }
    return render(request, 'invoicing/dashboard.html', context)


@login_required
def invoice_list(request):
    """List invoices - staff/finance sees all, clients see their own."""
    if request.user.is_staff_user:
        invoices = Invoice.objects.select_related('organization', 'contact').all()
        filter_form = InvoiceFilterForm(request.GET)
        invoices = _apply_invoice_filters(invoices, filter_form)
    else:
        invoices = _get_client_invoices(request.user)
        filter_form = None
    
    invoices = invoices.order_by('-issue_date')
    
    paginator = Paginator(invoices, 20)
    page = request.GET.get('page')
    invoices = paginator.get_page(page)
    
    context = {
        'invoices': invoices,
        'filter_form': filter_form,
        'status_choices': Invoice.Status.choices,
    }
    return render(request, 'invoicing/invoice_list.html', context)


@login_required
@finance_required
def invoice_create(request):
    """Create a new invoice."""
    if request.method == 'POST':
        form = InvoiceForm(request.POST, user=request.user)
        formset = InvoiceItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.save()
            
            formset.instance = invoice
            formset.save()
            
            messages.success(request, f'Invoice #{invoice.invoice_number} created successfully.')
            return redirect(INVOICE_DETAIL_URL, pk=invoice.pk)
    else:
        form = InvoiceForm(user=request.user)
        formset = InvoiceItemFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Invoice',
    }
    return render(request, 'invoicing/invoice_form.html', context)


@login_required
@finance_required
def invoice_edit(request, pk):
    """Edit an existing invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if invoice.status in [Invoice.Status.PAID, Invoice.Status.CANCELLED]:
        messages.error(request, 'Cannot edit a paid or cancelled invoice.')
        return redirect(INVOICE_DETAIL_URL, pk=pk)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice, user=request.user)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f'Invoice #{invoice.invoice_number} updated.')
            return redirect(INVOICE_DETAIL_URL, pk=pk)
    else:
        form = InvoiceForm(instance=invoice, user=request.user)
        formset = InvoiceItemFormSet(instance=invoice)
    
    context = {
        'form': form,
        'formset': formset,
        'invoice': invoice,
        'title': f'Edit Invoice #{invoice.invoice_number}',
    }
    return render(request, 'invoicing/invoice_form.html', context)


@login_required
def invoice_detail(request, pk):
    """Invoice detail view."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('organization', 'contact', 'created_by')
        .prefetch_related('items', 'payments'),
        pk=pk
    )
    
    # Check permission for non-staff
    if not request.user.is_staff_user:
        has_access = (
            invoice.contact and invoice.contact.user == request.user
        ) or invoice.organization.contacts.filter(user=request.user).exists()
        if not has_access:
            messages.error(request, 'You do not have access to this invoice.')
            return redirect(INVOICE_LIST_URL)
    
    context = {
        'invoice': invoice,
        'payments': invoice.payments.all(),
        'items': invoice.items.all(),
    }
    return render(request, 'invoicing/invoice_detail.html', context)


@login_required
@finance_required
@require_POST
def invoice_send(request, pk):
    """Mark invoice as sent."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if invoice.status == Invoice.Status.DRAFT:
        invoice.mark_as_sent()
        messages.success(request, f'Invoice #{invoice.invoice_number} marked as sent.')
    else:
        messages.warning(request, 'Invoice has already been sent.')
    
    return redirect(INVOICE_DETAIL_URL, pk=pk)


@login_required
def invoice_view(request, pk, token):
    """Public invoice view for clients (with token)."""
    import hashlib
    from django.conf import settings as django_settings
    
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Validate token using hash of invoice ID and secret key
    expected_token = hashlib.sha256(
        f"{invoice.pk}{django_settings.SECRET_KEY}".encode()
    ).hexdigest()[:32]
    
    if token != expected_token:
        messages.error(request, 'Invalid invoice access token.')
        return redirect(INVOICE_LIST_URL)
    
    context = {
        'invoice': invoice,
        'is_public_view': True,
    }
    return render(request, 'invoicing/invoice_public.html', context)


@login_required
@finance_required
def invoice_pdf(request, pk):
    """Generate PDF-ready view of invoice."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('organization', 'contact')
        .prefetch_related('items'),
        pk=pk
    )
    
    context = {
        'invoice': invoice,
        'is_pdf': True,
    }
    return render(request, 'invoicing/invoice_pdf.html', context)


@login_required
@finance_required
@require_POST
def invoice_void(request, pk):
    """Void an invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if invoice.status not in [Invoice.Status.PAID]:
        invoice.status = Invoice.Status.CANCELLED
        invoice.save()
        messages.success(request, f'Invoice #{invoice.invoice_number} has been cancelled.')
    else:
        messages.error(request, 'Cannot cancel a paid invoice.')
    
    return redirect(INVOICE_DETAIL_URL, pk=pk)


@login_required
@finance_required
@require_POST
def invoice_duplicate(request, pk):
    """Duplicate an invoice."""
    original = get_object_or_404(Invoice.objects.prefetch_related('items'), pk=pk)
    
    # Create new invoice
    new_invoice = Invoice.objects.create(
        organization=original.organization,
        contact=original.contact,
        issue_date=date.today(),
        due_date=date.today() + (original.due_date - original.issue_date),
        tax_rate=original.tax_rate,
        discount=original.discount,
        discount_description=original.discount_description,
        terms=original.terms,
        notes=original.notes,
        footer=original.footer,
        created_by=request.user,
    )
    
    # Duplicate items
    for item in original.items.all():
        InvoiceItem.objects.create(
            invoice=new_invoice,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
    
    messages.success(request, f'Invoice duplicated as #{new_invoice.invoice_number}.')
    return redirect(INVOICE_EDIT_URL, pk=new_invoice.pk)


@login_required
@finance_required
def payment_record(request, pk):
    """Record a manual payment for an invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if invoice.status in [Invoice.Status.PAID, Invoice.Status.CANCELLED]:
        messages.error(request, 'Cannot record payment for this invoice.')
        return redirect(INVOICE_DETAIL_URL, pk=pk)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, invoice=invoice)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.status = Payment.Status.COMPLETED
            payment.save()
            
            # Update invoice totals (don't call record_payment — it creates a duplicate Payment)
            invoice.amount_paid += payment.amount
            invoice.balance_due = invoice.total - invoice.amount_paid
            if invoice.balance_due <= 0:
                invoice.status = Invoice.Status.PAID
                invoice.paid_date = timezone.now().date()
            elif invoice.amount_paid > 0:
                invoice.status = Invoice.Status.PARTIAL
            invoice.save()
            
            messages.success(request, f'Payment of ${payment.amount} recorded.')
            return redirect(INVOICE_DETAIL_URL, pk=pk)
    else:
        form = PaymentForm(invoice=invoice)
    
    context = {
        'form': form,
        'invoice': invoice,
    }
    return render(request, 'invoicing/payment_form.html', context)


@login_required
def payment_list(request):
    """Payment history for the logged-in user."""
    if request.user.is_staff_user:
        payments = Payment.objects.select_related('invoice', 'invoice__organization').all()
    else:
        payments = Payment.objects.filter(
            Q(invoice__organization__contacts__user=request.user) |
            Q(invoice__contact__user=request.user)
        ).select_related('invoice', 'invoice__organization').distinct()
    
    payments = payments.order_by('-payment_date')
    
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    payments = paginator.get_page(page)
    
    context = {
        'payments': payments,
    }
    return render(request, 'invoicing/payment_list.html', context)


# Stripe Payment Views

@login_required
def invoice_pay(request, pk):
    """Payment page for an invoice using Stripe."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if invoice.status in [Invoice.Status.PAID, Invoice.Status.CANCELLED, Invoice.Status.DRAFT]:
        messages.error(request, 'This invoice cannot be paid online.')
        return redirect(INVOICE_DETAIL_URL, pk=pk)
    
    stripe_service = StripeService()
    return_url = request.build_absolute_uri(
        reverse('invoicing:payment_success', kwargs={'pk': pk})
    )
    
    result = stripe_service.create_payment_intent(invoice, return_url=return_url)
    
    if not result['success']:
        messages.error(request, 'Unable to initialize payment. Please try again.')
        return redirect(INVOICE_DETAIL_URL, pk=pk)
    
    context = {
        'invoice': invoice,
        'stripe_publishable_key': stripe_service.publishable_key,
        'client_secret': result['client_secret'],
    }
    return render(request, 'invoicing/invoice_pay.html', context)


@login_required
def payment_success(request, pk):
    """Payment success page."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    context = {
        'invoice': invoice,
    }
    return render(request, 'invoicing/payment_success.html', context)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    
    result = process_webhook_event(payload, sig_header)
    
    if result['success']:
        return HttpResponse(status=200)
    return HttpResponse(status=400)


# Recurring Invoices

@login_required
@finance_required
def recurring_invoice_list(request):
    """List recurring invoices."""
    recurring = RecurringInvoice.objects.select_related(
        'organization'
    ).order_by('-created_at')
    
    context = {
        'recurring_invoices': recurring,
    }
    return render(request, 'invoicing/recurring_list.html', context)


@login_required
@finance_required
def recurring_invoice_create(request):
    """Create a recurring invoice template."""
    if request.method == 'POST':
        form = RecurringInvoiceForm(request.POST, user=request.user)
        formset = RecurringInvoiceItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            recurring = form.save(commit=False)
            recurring.next_invoice_date = recurring.start_date
            recurring.created_by = request.user
            recurring.save()
            
            formset.instance = recurring
            formset.save()
            
            messages.success(request, f'Recurring invoice "{recurring.name}" created.')
            return redirect(RECURRING_LIST_URL)
    else:
        form = RecurringInvoiceForm(user=request.user)
        formset = RecurringInvoiceItemFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Recurring Invoice',
    }
    return render(request, 'invoicing/recurring_form.html', context)


@login_required
@finance_required
def recurring_invoice_edit(request, pk):
    """Edit a recurring invoice template."""
    recurring = get_object_or_404(RecurringInvoice, pk=pk)
    
    if request.method == 'POST':
        form = RecurringInvoiceForm(request.POST, instance=recurring, user=request.user)
        formset = RecurringInvoiceItemFormSet(request.POST, instance=recurring)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f'Recurring invoice "{recurring.name}" updated.')
            return redirect(RECURRING_LIST_URL)
    else:
        form = RecurringInvoiceForm(instance=recurring, user=request.user)
        formset = RecurringInvoiceItemFormSet(instance=recurring)
    
    context = {
        'form': form,
        'formset': formset,
        'recurring': recurring,
        'title': f'Edit Recurring Invoice: {recurring.name}',
    }
    return render(request, 'invoicing/recurring_form.html', context)


@login_required
@finance_required
@require_POST
def recurring_invoice_toggle(request, pk):
    """Toggle recurring invoice active status."""
    recurring = get_object_or_404(RecurringInvoice, pk=pk)
    recurring.is_active = not recurring.is_active
    recurring.save()
    
    status = 'activated' if recurring.is_active else 'deactivated'
    messages.success(request, f'Recurring invoice "{recurring.name}" {status}.')
    
    return redirect(RECURRING_LIST_URL)


# HTMX endpoints

@login_required
@require_GET
def get_organization_contacts(request):
    """HTMX endpoint to get contacts for an organization."""
    org_id = request.GET.get('organization_id')
    
    if not org_id:
        return HttpResponse(SELECT_CONTACT_OPTION)
    
    # Validate org_id is a valid integer to prevent injection
    try:
        org_id = int(org_id)
    except (ValueError, TypeError):
        return HttpResponse(SELECT_CONTACT_OPTION)
    
    contacts = Contact.objects.filter(organization_id=org_id)
    
    html = SELECT_CONTACT_OPTION
    for contact in contacts:
        html += f'<option value="{contact.id}">{escape(contact.full_name)}</option>'

    return HttpResponse(html, content_type='text/html')


# Quick invoice

@login_required
@finance_required
def quick_invoice(request):
    """Quick invoice creation form."""
    if request.method == 'POST':
        form = QuickInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.create_invoice(request.user)
            messages.success(request, f'Invoice #{invoice.invoice_number} created.')
            return redirect(INVOICE_EDIT_URL, pk=invoice.pk)
    else:
        form = QuickInvoiceForm()
    
    context = {
        'form': form,
    }
    return render(request, 'invoicing/quick_invoice.html', context)


# Email invoice

@login_required
@finance_required
def invoice_email(request, pk):
    """Email an invoice to client."""
    from django.core.mail import send_mail
    
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        form = InvoiceEmailForm(invoice=invoice, data=request.POST)
        if form.is_valid():
            # Get email details from form
            to_email = form.cleaned_data.get('to_email')
            subject = form.cleaned_data.get('subject')
            message = form.cleaned_data.get('message')
            
            # Send email synchronously (use Celery in production for async)
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[to_email],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error('Failed to send invoice email for invoice #%s: %s', invoice.invoice_number, e)
            
            if invoice.status == Invoice.Status.DRAFT:
                invoice.mark_as_sent()
            
            messages.success(request, f'Invoice #{invoice.invoice_number} email queued.')
            return redirect(INVOICE_DETAIL_URL, pk=pk)
    else:
        form = InvoiceEmailForm(invoice=invoice)
    
    context = {
        'form': form,
        'invoice': invoice,
    }
    return render(request, 'invoicing/invoice_email.html', context)
