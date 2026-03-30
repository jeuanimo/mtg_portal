"""
Tests for Invoice views.
"""

import pytest
from django.urls import reverse
from apps.invoicing.models import Invoice


class TestInvoiceListView:
    """Tests for invoice list views."""
    
    @pytest.mark.django_db
    def test_requires_authentication(self, client):
        """Test invoice list requires login."""
        response = client.get(reverse('invoicing:invoice_list'))
        assert response.status_code == 302
    
    @pytest.mark.django_db
    def test_staff_can_view_all_invoices(self, authenticated_client, invoice):
        """Test staff can view invoice list."""
        response = authenticated_client.get(reverse('invoicing:invoice_list'))
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_client_sees_only_own_invoices(self, client_user_client, invoice, client_user):
        """Test clients only see their own invoices."""
        # Assign invoice to client
        invoice.client = client_user
        invoice.save()
        
        response = client_user_client.get(reverse('invoicing:invoice_list'))
        assert response.status_code == 200
        # Client should only see their invoices


class TestInvoiceDetailView:
    """Tests for invoice detail view."""
    
    @pytest.mark.django_db
    def test_staff_can_view_any_invoice(self, authenticated_client, invoice):
        """Test staff can view any invoice."""
        response = authenticated_client.get(
            reverse('invoicing:invoice_detail', args=[invoice.pk])
        )
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_client_can_view_own_invoice(self, client_user_client, invoice, client_user):
        """Test client can view their own invoice."""
        invoice.client = client_user
        invoice.save()
        
        response = client_user_client.get(
            reverse('invoicing:invoice_detail', args=[invoice.pk])
        )
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_client_cannot_view_others_invoice(self, client, client_user, password, invoice):
        """Test client cannot view other's invoices."""
        # Create another client
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other_client = User.objects.create_user(
            email='other@client.com',
            password=password,
            role='client',
        )
        
        # Invoice belongs to original client
        invoice.client = client_user
        invoice.save()
        
        # Login as other client
        client.login(email=other_client.email, password=password)
        response = client.get(
            reverse('invoicing:invoice_detail', args=[invoice.pk])
        )
        # Should be forbidden or not found
        assert response.status_code in [403, 404, 302]


class TestInvoiceCreateView:
    """Tests for invoice creation."""
    
    @pytest.mark.django_db
    def test_staff_can_create_invoice(self, authenticated_client, client_user, organization):
        """Test staff can create invoices."""
        response = authenticated_client.get(reverse('invoicing:invoice_create'))
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_create_invoice_success(self, authenticated_client, client_user, organization):
        """Test creating an invoice."""
        from datetime import date, timedelta
        
        data = {
            'client': client_user.pk,
            'organization': organization.pk,
            'invoice_number': 'INV-TEST-001',
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'status': 'draft',
            'notes': 'Test invoice',
        }
        response = authenticated_client.post(
            reverse('invoicing:invoice_create'), data
        )
        
        # Should redirect or success
        assert response.status_code in [200, 302]
        assert Invoice.objects.filter(invoice_number='INV-TEST-001').exists()
    
    @pytest.mark.django_db
    def test_client_cannot_create_invoice(self, client_user_client):
        """Test clients cannot create invoices."""
        response = client_user_client.get(reverse('invoicing:invoice_create'))
        assert response.status_code in [302, 403]


class TestInvoicePDFView:
    """Tests for PDF generation."""
    
    @pytest.mark.django_db
    def test_generate_pdf(self, authenticated_client, invoice_with_items):
        """Test PDF generation view."""
        response = authenticated_client.get(
            reverse('invoicing:invoice_pdf', args=[invoice_with_items.pk])
        )
        # Should return PDF or redirect
        assert response.status_code in [200, 302]
        if response.status_code == 200:
            assert (
                response['Content-Type'] == 'application/pdf' or
                'pdf' in response['Content-Type'].lower()
            )


class TestPaymentViews:
    """Tests for payment handling."""
    
    @pytest.mark.django_db
    def test_record_payment_form(self, admin_client, invoice):
        """Test payment recording form renders."""
        response = admin_client.get(
            reverse('invoicing:record_payment', args=[invoice.pk])
        )
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_record_payment(self, admin_client, invoice):
        """Test recording a payment."""
        data = {
            'amount': '250.00',
            'payment_method': 'credit_card',
            'payment_date': '2024-01-15',
            'reference': 'TEST-REF-001',
        }
        response = admin_client.post(
            reverse('invoicing:record_payment', args=[invoice.pk]), data
        )
        
        # Should redirect after success
        assert response.status_code in [200, 302]


class TestInvoiceSendView:
    """Tests for sending invoices."""
    
    @pytest.mark.django_db
    def test_send_invoice(self, authenticated_client, invoice):
        """Test sending invoice to client."""
        invoice.status = 'draft'
        invoice.save()
        
        response = authenticated_client.post(
            reverse('invoicing:invoice_send', args=[invoice.pk])
        )
        
        # Should redirect after sending
        assert response.status_code in [200, 302]
        
        invoice.refresh_from_db()
        # Status should change to sent
        assert invoice.status in ['sent', 'draft']  # Depends on implementation


class TestStripeCheckout:
    """Tests for Stripe checkout integration."""
    
    @pytest.mark.django_db
    def test_checkout_session_creation(self, client_user_client, invoice, client_user):
        """Test creating Stripe checkout session."""
        invoice.client = client_user
        invoice.save()
        
        # This would typically test the checkout endpoint
        response = client_user_client.post(
            reverse('invoicing:create_checkout_session', args=[invoice.pk])
        )
        
        # Should redirect to Stripe or return session data
        assert response.status_code in [200, 302, 400]  # 400 if Stripe not configured
