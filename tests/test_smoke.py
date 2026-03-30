"""
Smoke tests - Quick tests to verify major pages load without errors.

These tests ensure basic functionality works:
- Pages render without 500 errors
- Authentication works
- Critical endpoints are accessible
"""

import pytest
from django.urls import reverse


class TestPublicPages:
    """Smoke tests for public pages (no auth required)."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_home_page(self, client):
        """Test home page loads."""
        response = client.get(reverse('public:home'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_about_page(self, client):
        """Test about page loads."""
        response = client.get(reverse('public:about'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_services_page(self, client):
        """Test services page loads."""
        response = client.get(reverse('public:services'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_contact_page(self, client):
        """Test contact page loads."""
        response = client.get(reverse('public:contact'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_login_page(self, client):
        """Test login page loads."""
        response = client.get(reverse('account_login'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_signup_page(self, client):
        """Test signup page loads."""
        response = client.get(reverse('account_signup'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health/')
        assert response.status_code == 200


class TestAuthenticatedPages:
    """Smoke tests for authenticated pages."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_dashboard(self, authenticated_client):
        """Test dashboard loads for authenticated users."""
        response = authenticated_client.get(reverse('dashboard:index'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_profile_page(self, authenticated_client):
        """Test profile page loads."""
        response = authenticated_client.get(reverse('accounts:profile'))
        assert response.status_code == 200


class TestCRMPages:
    """Smoke tests for CRM pages."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_lead_list(self, authenticated_client):
        """Test lead list loads."""
        response = authenticated_client.get(reverse('crm:lead_list'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_contact_list(self, authenticated_client):
        """Test contact list loads."""
        response = authenticated_client.get(reverse('crm:contact_list'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_organization_list(self, authenticated_client):
        """Test organization list loads."""
        response = authenticated_client.get(reverse('crm:organization_list'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_lead_create_form(self, authenticated_client):
        """Test lead create form loads."""
        response = authenticated_client.get(reverse('crm:lead_create'))
        assert response.status_code == 200


class TestInvoicingPages:
    """Smoke tests for invoicing pages."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_invoice_list(self, authenticated_client):
        """Test invoice list loads."""
        response = authenticated_client.get(reverse('invoicing:invoice_list'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_invoice_create_form(self, authenticated_client):
        """Test invoice create form loads."""
        response = authenticated_client.get(reverse('invoicing:invoice_create'))
        assert response.status_code == 200


class TestTicketPages:
    """Smoke tests for ticket pages."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_ticket_list(self, authenticated_client):
        """Test ticket list loads."""
        response = authenticated_client.get(reverse('tickets:ticket_list'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_ticket_create_form(self, authenticated_client):
        """Test ticket create form loads."""
        response = authenticated_client.get(reverse('tickets:ticket_create'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_ticket_detail(self, authenticated_client, ticket):
        """Test ticket detail loads."""
        response = authenticated_client.get(
            reverse('tickets:ticket_detail', args=[ticket.pk])
        )
        assert response.status_code == 200


class TestMeetingPages:
    """Smoke tests for meeting pages."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_meeting_list(self, authenticated_client):
        """Test meeting list loads."""
        response = authenticated_client.get(reverse('meetings:meeting_list'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_meeting_create_form(self, authenticated_client):
        """Test meeting create form loads."""
        response = authenticated_client.get(reverse('meetings:meeting_create'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_calendar_view(self, authenticated_client):
        """Test calendar view loads."""
        response = authenticated_client.get(reverse('meetings:calendar'))
        assert response.status_code == 200


class TestAdminPages:
    """Smoke tests for admin pages."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_admin_index(self, admin_client):
        """Test Django admin loads."""
        response = admin_client.get('/admin/')
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_admin_users(self, admin_client):
        """Test admin users list loads."""
        response = admin_client.get('/admin/accounts/user/')
        assert response.status_code == 200


class TestAPIEndpoints:
    """Smoke tests for API endpoints (if any)."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_api_health(self, client):
        """Test API health endpoint."""
        response = client.get('/api/health/')
        # May or may not exist
        assert response.status_code in [200, 404]


class TestErrorPages:
    """Tests for error page handling."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_404_page(self, client):
        """Test 404 error page."""
        response = client.get('/nonexistent-page-that-does-not-exist/')
        assert response.status_code == 404
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_unauthenticated_redirect(self, client):
        """Test unauthenticated users are redirected."""
        response = client.get(reverse('dashboard:index'))
        assert response.status_code == 302
        assert 'login' in response.url or 'account' in response.url


class TestClientPortalPages:
    """Smoke tests for client-specific pages."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_client_dashboard(self, client_user_client):
        """Test client dashboard loads."""
        response = client_user_client.get(reverse('dashboard:index'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_client_tickets(self, client_user_client):
        """Test client can access tickets."""
        response = client_user_client.get(reverse('tickets:ticket_list'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_client_invoices(self, client_user_client):
        """Test client can access invoices."""
        response = client_user_client.get(reverse('invoicing:invoice_list'))
        assert response.status_code == 200


class TestRoleDashboards:
    """Smoke tests for role-specific dashboards."""
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_admin_dashboard(self, admin_client):
        """Test admin dashboard loads."""
        response = admin_client.get(reverse('dashboard:index'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_staff_dashboard(self, authenticated_client):
        """Test staff dashboard loads."""
        response = authenticated_client.get(reverse('dashboard:index'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_consultant_dashboard(self, client, consultant_user, password):
        """Test consultant dashboard loads."""
        client.login(email=consultant_user.email, password=password)
        response = client.get(reverse('dashboard:index'))
        assert response.status_code == 200
    
    @pytest.mark.smoke
    @pytest.mark.django_db
    def test_finance_dashboard(self, client, finance_user, password):
        """Test finance dashboard loads."""
        client.login(email=finance_user.email, password=password)
        response = client.get(reverse('dashboard:index'))
        assert response.status_code == 200
