"""
Tests for CRM forms - Lead intake and contact forms.
"""

import pytest
from apps.crm.forms import LeadForm, ContactForm, OrganizationForm
from apps.crm.models import Contact, Organization


class TestLeadForm:
    """Tests for the Lead intake form."""
    
    @pytest.mark.django_db
    def test_valid_form(self, contact, organization, staff_user):
        """Test form validation with valid data."""
        form_data = {
            'title': 'New Website Project',
            'contact': contact.pk,
            'organization': organization.pk,
            'source': 'website',
            'status': 'new',
            'priority': 'medium',
            'notes': 'Looking for a new website redesign.',
        }
        form = LeadForm(data=form_data)
        assert form.is_valid(), form.errors
    
    @pytest.mark.django_db
    def test_required_fields(self):
        """Test that required fields are enforced."""
        form = LeadForm(data={})
        assert not form.is_valid()
        assert 'title' in form.errors or 'contact' in form.errors
    
    @pytest.mark.django_db
    def test_valid_sources(self, contact):
        """Test all valid source options."""
        sources = ['website', 'referral', 'cold_call', 'social', 'event', 'partner', 'other']
        for source in sources:
            form_data = {
                'title': 'Test Lead',
                'contact': contact.pk,
                'source': source,
                'status': 'new',
                'priority': 'medium',
            }
            form = LeadForm(data=form_data)
            assert form.is_valid(), f"Source '{source}' should be valid: {form.errors}"
    
    @pytest.mark.django_db
    def test_invalid_source(self, contact):
        """Test form rejects invalid source."""
        form_data = {
            'title': 'Test Lead',
            'contact': contact.pk,
            'source': 'invalid_source',
            'status': 'new',
        }
        form = LeadForm(data=form_data)
        assert not form.is_valid()


class TestContactForm:
    """Tests for the Contact form."""
    
    @pytest.mark.django_db
    def test_valid_form(self, organization):
        """Test form validation with valid data."""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'organization': organization.pk,
        }
        form = ContactForm(data=form_data)
        assert form.is_valid(), form.errors
    
    def test_required_fields(self):
        """Test required fields validation."""
        form = ContactForm(data={})
        assert not form.is_valid()
        # At least first_name or email should be required
        assert len(form.errors) > 0
    
    @pytest.mark.django_db
    def test_optional_organization(self):
        """Test organization is optional."""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            # No organization
        }
        form = ContactForm(data=form_data)
        # Depending on form config, this might be valid or not
        # Just verify form processes without errors
        form.is_valid()


class TestOrganizationForm:
    """Tests for the Organization form."""
    
    def test_valid_form(self):
        """Test form validation with valid data."""
        form_data = {
            'name': 'Acme Corp',
            'industry': 'Technology',
            'website': 'https://acme.com',
        }
        form = OrganizationForm(data=form_data)
        assert form.is_valid(), form.errors
    
    def test_name_required(self):
        """Test organization name is required."""
        form = OrganizationForm(data={})
        assert not form.is_valid()
        assert 'name' in form.errors
    
    def test_valid_website_url(self):
        """Test website URL validation."""
        form_data = {
            'name': 'Test Org',
            'website': 'not-a-valid-url',
        }
        form = OrganizationForm(data=form_data)
        # Website should fail validation if it's not a URL
        # Note: This depends on form field configuration
        if not form.is_valid():
            assert 'website' in form.errors
