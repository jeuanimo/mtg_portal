from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from apps.core.models import TimeStampedModel
from apps.crm.models import Organization, Contact


class Invoice(TimeStampedModel):
    """Client invoices."""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        VIEWED = 'viewed', 'Viewed'
        PARTIAL = 'partial', 'Partially Paid'
        PAID = 'paid', 'Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'
    
    # Invoice details
    invoice_number = models.CharField(max_length=50, unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name='invoices'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # Dates
    issue_date = models.DateField()
    due_date = models.DateField()
    sent_date = models.DateTimeField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_description = models.CharField(max_length=200, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Notes
    notes = models.TextField(blank=True, help_text='Internal notes')
    terms = models.TextField(blank=True, help_text='Terms displayed on invoice')
    footer = models.TextField(blank=True, help_text='Footer text for invoice')
    
    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    
    # Recurring invoice reference
    recurring_invoice = models.ForeignKey(
        'RecurringInvoice', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='generated_invoices'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_invoices'
    )
    
    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['status', '-issue_date']),
            models.Index(fields=['organization', '-issue_date']),
            models.Index(fields=['due_date', 'status']),
        ]

    OUTSTANDING_STATUSES = (
        Status.SENT,
        Status.VIEWED,
        Status.PARTIAL,
        Status.OVERDUE,
    )
    NON_EDITABLE_STATUSES = (Status.PAID, Status.CANCELLED)
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.organization.name}"

    @property
    def total_amount(self):
        """Backwards-compatible alias for stale views/templates."""
        return self.total

    @property
    def paid_amount(self):
        """Backwards-compatible alias for stale views/templates."""
        return self.amount_paid

    @property
    def discount_amount(self):
        """Backwards-compatible alias for stale views/templates."""
        return self.discount

    @property
    def can_send(self):
        return self.status == self.Status.DRAFT

    @property
    def can_record_payment(self):
        return self.status not in self.NON_EDITABLE_STATUSES

    @property
    def can_pay_online(self):
        return self.status in self.OUTSTANDING_STATUSES

    @property
    def can_cancel(self):
        return self.status not in self.NON_EDITABLE_STATUSES
    
    def calculate_totals(self):
        """Recalculate all totals from line items."""
        self.subtotal = sum(item.line_total for item in self.items.all())
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount - self.discount
        self.balance_due = self.total - self.amount_paid
        self.save()
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last = Invoice.objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.invoice_number = f"INV-{next_num:05d}"
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        if self.status in self.NON_EDITABLE_STATUSES:
            return False
        return self.due_date < timezone.now().date()
    
    def mark_as_sent(self):
        """Mark invoice as sent and record the timestamp."""
        self.status = self.Status.SENT
        self.sent_date = timezone.now()
        self.save()
    
    def record_payment(self, amount, method='stripe', **kwargs):
        """Record a payment against this invoice."""
        payment = Payment.objects.create(
            invoice=self,
            amount=amount,
            method=method,
            status=Payment.Status.COMPLETED,
            **kwargs
        )
        
        self.amount_paid += Decimal(str(amount))
        self.balance_due = self.total - self.amount_paid
        
        if self.balance_due <= 0:
            self.status = self.Status.PAID
            self.paid_date = timezone.now().date()
        elif self.amount_paid > 0:
            self.status = self.Status.PARTIAL
        
        self.save()
        return payment
    
    def get_payment_url(self):
        """Get the URL for client to pay this invoice."""
        from django.urls import reverse
        return reverse('invoicing:invoice_pay', kwargs={'pk': self.pk})


class InvoiceItem(TimeStampedModel):
    """Line items on an invoice."""
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = 'Invoice Item'
        verbose_name_plural = 'Invoice Items'
    
    def __str__(self):
        return f"{self.description} - {self.line_total}"

    @property
    def total(self):
        """Backwards-compatible alias for older templates."""
        return self.line_total
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Payment(TimeStampedModel):
    """Payment records."""
    
    class Method(models.TextChoices):
        STRIPE = 'stripe', 'Credit Card (Stripe)'
        CHECK = 'check', 'Check'
        WIRE = 'wire', 'Wire Transfer'
        ACH = 'ach', 'ACH Transfer'
        CASH = 'cash', 'Cash'
        OTHER = 'other', 'Other'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
        PARTIALLY_REFUNDED = 'partial_refund', 'Partially Refunded'
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Stripe fields
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_charge_id = models.CharField(max_length=100, blank=True)
    stripe_refund_id = models.CharField(max_length=100, blank=True)
    
    # Card details (last 4 only for display)
    card_brand = models.CharField(max_length=20, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    
    # Refund info
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    refund_reason = models.TextField(blank=True)
    
    # Other payment details
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    receipt_url = models.URLField(blank=True)
    
    payment_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['invoice', '-payment_date']),
            models.Index(fields=['status', '-payment_date']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]
    
    def __str__(self):
        return f"Payment of ${self.amount} for Invoice #{self.invoice.invoice_number}"
    
    @property
    def is_refundable(self):
        return self.status == self.Status.COMPLETED and self.method == self.Method.STRIPE


class RecurringInvoice(TimeStampedModel):
    """Template for recurring invoices."""
    
    class Frequency(models.TextChoices):
        WEEKLY = 'weekly', 'Weekly'
        BIWEEKLY = 'biweekly', 'Bi-Weekly'
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        ANNUALLY = 'annually', 'Annually'
    
    name = models.CharField(max_length=200)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='recurring_invoices'
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    # Schedule
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text='Leave blank for indefinite')
    next_invoice_date = models.DateField()
    days_until_due = models.PositiveSmallIntegerField(default=30)
    
    # Invoice template
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    terms = models.TextField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_recurring_invoices'
    )
    
    class Meta:
        verbose_name = 'Recurring Invoice'
        verbose_name_plural = 'Recurring Invoices'
    
    def __str__(self):
        return f"{self.name} - {self.organization.name} ({self.get_frequency_display()})"


class RecurringInvoiceItem(TimeStampedModel):
    """Line items for recurring invoice template."""
    
    recurring_invoice = models.ForeignKey(
        RecurringInvoice, on_delete=models.CASCADE, related_name='items'
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = 'Recurring Invoice Item'
        verbose_name_plural = 'Recurring Invoice Items'
    
    def __str__(self):
        return self.description
