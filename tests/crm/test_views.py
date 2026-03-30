"""
Tests for CRM views - Lead, Contact, Organization views.
"""

import pytest
from django.urls import reverse
from apps.crm.models import Lead, Contact, Organization


class TestLeadListView:
    """Tests for lead list view."""
    
    @pytest.mark.django_db
    def test_requires_authentication(self, client):
        """Test lead list requires login."""
        response = client.get(reverse('crm:lead_list'))
        assert response.status_code == 302  # Redirect to login
    
    @pytest.mark.django_db
    def test_staff_can_access(self, authenticated_client, lead):
        """Test staff can access lead list."""
        response = authenticated_client.get(reverse('crm:lead_list'))
        assert response.status_code == 200
        assert lead.title.encode() in response.content
    
    @pytest.mark.django_db
    def test_client_cannot_access(self, client_user_client):
        """Test clients cannot access lead list."""
        response = client_user_client.get(reverse('crm:lead_list'))
        assert response.status_code in [302, 403]


class TestLeadDetailView:
    """Tests for lead detail view."""
    
    @pytest.mark.django_db
    def test_lead_detail_renders(self, authenticated_client, lead):
        """Test lead detail page renders."""
        response = authenticated_client.get(reverse('crm:lead_detail', args=[lead.pk]))
        assert response.status_code == 200
        assert lead.title.encode() in response.content
    
    @pytest.mark.django_db
    def test_nonexistent_lead_404(self, authenticated_client):
        """Test 404 for nonexistent lead."""
        response = authenticated_client.get(reverse('crm:lead_detail', args=[99999]))
        assert response.status_code == 404


class TestLeadCreateView:
    """Tests for lead creation."""
    
    @pytest.mark.django_db
    def test_create_lead_form_renders(self, authenticated_client):
        """Test create lead form renders."""
        response = authenticated_client.get(reverse('crm:lead_create'))
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_create_lead_success(self, authenticated_client, contact, organization):
        """Test creating a new lead."""
        data = {
            'title': 'Test Lead Creation',
            'contact': contact.pk,
            'organization': organization.pk,
            'source': 'website',
            'status': 'new',
            'priority': 'medium',
            'notes': 'Test description',
        }
        response = authenticated_client.post(reverse('crm:lead_create'), data)
        
        # Should redirect after success
        assert response.status_code in [200, 302]
        
        # Lead should be created
        assert Lead.objects.filter(title='Test Lead Creation').exists()
    
    @pytest.mark.django_db
    def test_create_lead_invalid_data(self, authenticated_client):
        """Test creating lead with invalid data."""
        data = {
            'title': '',  # Required field empty
        }
        response = authenticated_client.post(reverse('crm:lead_create'), data)
        
        # Should stay on form with errors
        assert response.status_code == 200
        assert Lead.objects.filter(title='').count() == 0


class TestLeadUpdateView:
    """Tests for lead updates."""
    
    @pytest.mark.django_db
    def test_update_lead(self, authenticated_client, lead):
        """Test updating a lead."""
        data = {
            'title': 'Updated Title',
            'contact': lead.contact.pk,
            'organization': lead.organization.pk if lead.organization else '',
            'source': lead.source,
            'status': 'discovery',
            'priority': lead.priority,
            'notes': lead.notes or '',
        }
        response = authenticated_client.post(
            reverse('crm:lead_update', args=[lead.pk]), data
        )
        
        lead.refresh_from_db()
        assert lead.title == 'Updated Title'
        assert lead.status == 'discovery'


class TestLeadDeleteView:
    """Tests for lead deletion."""
    
    @pytest.mark.django_db
    def test_delete_lead(self, authenticated_client, lead):
        """Test deleting a lead."""
        lead_pk = lead.pk
        response = authenticated_client.post(reverse('crm:lead_delete', args=[lead_pk]))
        
        # Should redirect after delete
        assert response.status_code in [200, 302]
        
        # Lead should be deleted
        assert not Lead.objects.filter(pk=lead_pk).exists()


class TestContactViews:
    """Tests for contact views."""
    
    @pytest.mark.django_db
    def test_contact_list(self, authenticated_client, contact):
        """Test contact list view."""
        response = authenticated_client.get(reverse('crm:contact_list'))
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_contact_detail(self, authenticated_client, contact):
        """Test contact detail view."""
        response = authenticated_client.get(reverse('crm:contact_detail', args=[contact.pk]))
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_create_contact(self, authenticated_client):
        """Test creating a contact."""
        data = {
            'first_name': 'New',
            'last_name': 'Contact',
            'email': 'new@contact.com',
        }
        response = authenticated_client.post(reverse('crm:contact_create'), data)
        assert Contact.objects.filter(email='new@contact.com').exists()


class TestOrganizationViews:
    """Tests for organization views."""
    
    @pytest.mark.django_db
    def test_organization_list(self, authenticated_client, organization):
        """Test organization list view."""
        response = authenticated_client.get(reverse('crm:organization_list'))
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_organization_detail(self, authenticated_client, organization):
        """Test organization detail view."""
        response = authenticated_client.get(reverse('crm:organization_detail', args=[organization.pk]))
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_create_organization(self, authenticated_client):
        """Test creating an organization."""
        data = {
            'name': 'New Organization',
            'industry': 'Finance',
        }
        response = authenticated_client.post(reverse('crm:organization_create'), data)
        assert Organization.objects.filter(name='New Organization').exists()


class TestPublicLeadIntake:
    """Tests for public lead intake form."""
    
    @pytest.mark.django_db
    def test_public_lead_form_renders(self, client):
        """Test public lead form is accessible without login."""
        response = client.get(reverse('public:contact'))  # Assuming this exists
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_public_lead_submission(self, client):
        """Test submitting a lead through public form."""
        data = {
            'name': 'Public Lead',
            'email': 'public@example.com',
            'phone': '555-987-6543',
            'message': 'I need IT services.',
        }
        response = client.post(reverse('public:contact'), data)
        
        # Should redirect to thank you page or show success
        assert response.status_code in [200, 302]
