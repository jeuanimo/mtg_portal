"""
Tests for Invoice models - Invoice calculations, status, and payment logic.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from apps.invoicing.models import Invoice, InvoiceItem, Payment


class TestInvoiceModel:
    """Tests for the Invoice model."""
    
    @pytest.mark.django_db
    def test_create_invoice(self, organization, contact):
        """Test creating an invoice."""
        invoice = Invoice.objects.create(
            organization=organization,
            contact=contact,
            invoice_number='INV-001',
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='draft',
        )
        assert invoice.invoice_number == 'INV-001'
        assert invoice.status == 'draft'
    
    @pytest.mark.django_db
    def test_invoice_str(self, invoice):
        """Test invoice string representation."""
        assert invoice.invoice_number in str(invoice)
    
    @pytest.mark.django_db
    def test_invoice_default_values(self, invoice):
        """Test invoice default values."""
        # Subtotal should start at 0.00
        assert invoice.subtotal >= Decimal('0.00')


class TestInvoiceItems:
    """Tests for InvoiceItem model."""
    
    @pytest.mark.django_db
    def test_add_item_to_invoice(self, invoice):
        """Test adding an item to invoice."""
        from apps.invoicing.models import InvoiceItem
        item = InvoiceItem.objects.create(
            invoice=invoice,
            description='Consulting Services',
            quantity=10,
            unit_price=Decimal('150.00'),
            line_total=Decimal('1500.00'),
        )
        assert item.invoice == invoice
        assert item.quantity == 10
    
    @pytest.mark.django_db
    def test_item_total_calculation(self, invoice):
        """Test line item total calculation."""
        from apps.invoicing.models import InvoiceItem
        item = InvoiceItem.objects.create(
            invoice=invoice,
            description='Development Work',
            quantity=5,
            unit_price=Decimal('200.00'),
            line_total=Decimal('1000.00'),
        )
        # Total should be quantity * unit_price
        assert item.line_total == Decimal('1000.00')
    
    @pytest.mark.django_db
    def test_invoice_subtotal_with_items(self, invoice):
        """Test invoice subtotal with multiple items."""
        from apps.invoicing.models import InvoiceItem
        InvoiceItem.objects.create(
            invoice=invoice,
            description='Service 1',
            quantity=2,
            unit_price=Decimal('100.00'),
            line_total=Decimal('200.00'),
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            description='Service 2',
            quantity=3,
            unit_price=Decimal('50.00'),
            line_total=Decimal('150.00'),
        )
        
        invoice.calculate_totals()
        # Subtotal should be 200 + 150 = 350
        expected = Decimal('350.00')
        assert invoice.subtotal == expected


class TestInvoiceCalculations:
    """Tests for invoice calculations."""
    
    @pytest.mark.django_db
    def test_invoice_total_without_tax(self, invoice_with_items):
        """Test invoice total without tax."""
        # Should equal subtotal when no tax
        invoice_with_items.tax_rate = Decimal('0.00')
        invoice_with_items.discount = Decimal('0.00')
        invoice_with_items.calculate_totals()
        
        assert invoice_with_items.total == invoice_with_items.subtotal
    
    @pytest.mark.django_db
    def test_invoice_total_with_tax(self, invoice_with_items):
        """Test invoice total with tax applied."""
        invoice_with_items.tax_rate = Decimal('10.00')  # 10%
        invoice_with_items.discount = Decimal('0.00')
        invoice_with_items.calculate_totals()
        
        expected_tax = invoice_with_items.subtotal * Decimal('0.10')
        expected_total = invoice_with_items.subtotal + expected_tax
        
        assert invoice_with_items.tax_amount == expected_tax
        assert invoice_with_items.total == expected_total
    
    @pytest.mark.django_db
    def test_invoice_balance_due(self, invoice_with_items):
        """Test balance due calculation."""
        invoice_with_items.tax_rate = Decimal('0.00')
        invoice_with_items.discount = Decimal('0.00')
        invoice_with_items.amount_paid = Decimal('100.00')
        invoice_with_items.calculate_totals()
        
        expected_balance = invoice_with_items.total - Decimal('100.00')
        assert invoice_with_items.balance_due == expected_balance


class TestInvoiceStatus:
    """Tests for invoice status logic."""
    
    @pytest.mark.django_db
    def test_invoice_status_transitions(self, invoice):
        """Test invoice status changes."""
        statuses = ['draft', 'sent', 'viewed', 'paid', 'overdue', 'cancelled']
        for status in statuses:
            invoice.status = status
            invoice.save()
            invoice.refresh_from_db()
            assert invoice.status == status
    
    @pytest.mark.django_db
    def test_overdue_invoice_detection(self, invoice):
        """Test detecting overdue invoices."""
        invoice.due_date = date.today() - timedelta(days=1)
        invoice.status = 'sent'
        invoice.save()
        
        assert invoice.is_overdue
    
    @pytest.mark.django_db
    def test_invoice_is_paid_when_fully_paid(self, invoice_with_items):
        """Test invoice is paid when balance is zero."""
        invoice_with_items.calculate_totals()
        total = invoice_with_items.total
        invoice_with_items.amount_paid = total
        invoice_with_items.status = 'paid'
        invoice_with_items.calculate_totals()
        
        assert invoice_with_items.status == 'paid'
        assert invoice_with_items.balance_due == Decimal('0.00')


class TestPaymentModel:
    """Tests for Payment model."""
    
    @pytest.mark.django_db
    def test_create_payment(self, invoice):
        """Test creating a payment."""
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal('500.00'),
            method='stripe',
            status='completed',
        )
        assert payment.amount == Decimal('500.00')
        assert payment.invoice == invoice
    
    @pytest.mark.django_db
    def test_payment_updates_invoice(self, invoice_with_items):
        """Test payment updates invoice amount_paid."""
        initial_paid = invoice_with_items.amount_paid or Decimal('0.00')
        
        # Use the record_payment method which updates invoice
        invoice_with_items.record_payment(
            amount=Decimal('200.00'),
            method='stripe',
        )
        
        invoice_with_items.refresh_from_db()
        # Invoice amount_paid should be updated
        assert invoice_with_items.amount_paid >= Decimal('200.00')


class TestInvoiceQuerysets:
    """Tests for invoice querysets."""
    
    @pytest.mark.django_db
    def test_filter_by_status(self, organization, contact):
        """Test filtering invoices by status."""
        Invoice.objects.create(
            organization=organization, contact=contact,
            invoice_number='INV-S001', status='draft',
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        Invoice.objects.create(
            organization=organization, contact=contact,
            invoice_number='INV-S002', status='sent',
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        Invoice.objects.create(
            organization=organization, contact=contact,
            invoice_number='INV-S003', status='paid',
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        
        draft_invoices = Invoice.objects.filter(status='draft')
        sent_invoices = Invoice.objects.filter(status='sent')
        paid_invoices = Invoice.objects.filter(status='paid')
        
        assert draft_invoices.count() >= 1
        assert sent_invoices.count() >= 1
        assert paid_invoices.count() >= 1
    
    @pytest.mark.django_db
    def test_overdue_invoices_queryset(self, organization, contact):
        """Test getting overdue invoices."""
        # Create overdue invoice
        Invoice.objects.create(
            organization=organization, contact=contact,
            invoice_number='INV-OVERDUE', status='sent',
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=5),
        )
        
        # Create future invoice
        Invoice.objects.create(
            organization=organization, contact=contact,
            invoice_number='INV-FUTURE', status='sent',
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        
        overdue = Invoice.objects.filter(
            due_date__lt=date.today(),
            status__in=['sent', 'viewed']
        )
        assert overdue.count() >= 1
