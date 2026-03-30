from django.contrib import admin
from .models import Invoice, InvoiceItem, Payment, RecurringInvoice, RecurringInvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['stripe_payment_intent_id', 'stripe_charge_id', 'payment_date']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'organization', 'status', 'total', 'balance_due', 'due_date', 'is_overdue', 'created_at']
    list_filter = ['status', 'issue_date', 'due_date']
    search_fields = ['invoice_number', 'organization__name']
    date_hierarchy = 'issue_date'
    readonly_fields = ['subtotal', 'tax_amount', 'total', 'balance_due', 'is_overdue', 'created_at', 'updated_at']
    inlines = [InvoiceItemInline, PaymentInline]
    
    fieldsets = (
        ('Invoice Details', {
            'fields': ('invoice_number', 'organization', 'contact', 'status')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'sent_date', 'paid_date')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'discount_amount', 'discount_description', 'total', 'paid_amount', 'balance_due')
        }),
        ('Notes', {
            'fields': ('notes', 'terms', 'footer')
        }),
        ('Stripe', {
            'fields': ('stripe_invoice_id',),
            'classes': ('collapse',)
        }),
        ('Recurring', {
            'fields': ('recurring_invoice',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'method', 'status', 'payment_date']
    list_filter = ['status', 'method', 'payment_date']
    search_fields = ['invoice__invoice_number', 'reference_number', 'stripe_payment_intent_id']
    date_hierarchy = 'payment_date'
    readonly_fields = ['payment_date', 'stripe_payment_intent_id', 'stripe_charge_id', 'stripe_refund_id', 'receipt_url']
    
    fieldsets = (
        ('Payment Info', {
            'fields': ('invoice', 'amount', 'method', 'status')
        }),
        ('References', {
            'fields': ('reference_number', 'notes')
        }),
        ('Stripe Details', {
            'fields': ('stripe_payment_intent_id', 'stripe_charge_id', 'card_brand', 'card_last4', 'receipt_url'),
            'classes': ('collapse',)
        }),
        ('Refund Info', {
            'fields': ('refunded_amount', 'refund_reason', 'stripe_refund_id'),
            'classes': ('collapse',)
        }),
    )


class RecurringInvoiceItemInline(admin.TabularInline):
    model = RecurringInvoiceItem
    extra = 1


@admin.register(RecurringInvoice)
class RecurringInvoiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'frequency', 'next_invoice_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'frequency']
    search_fields = ['name', 'organization__name']
    inlines = [RecurringInvoiceItemInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'organization', 'contact', 'is_active')
        }),
        ('Schedule', {
            'fields': ('frequency', 'start_date', 'end_date', 'next_invoice_date', 'days_until_due')
        }),
        ('Invoice Template', {
            'fields': ('tax_rate', 'terms')
        }),
    )
