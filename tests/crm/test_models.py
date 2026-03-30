"""
Tests for CRM models - Lead, Contact, Organization.
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from apps.crm.models import Lead, Contact, Organization


class TestOrganizationModel:
    """Tests for the Organization model."""
    
    @pytest.mark.django_db
    def test_create_organization(self):
        """Test creating an organization."""
        org = Organization.objects.create(
            name='Test Company',
            industry='Technology',
            website='https://testcompany.com',
        )
        assert org.name == 'Test Company'
        assert str(org) == 'Test Company'
    
    @pytest.mark.django_db
    def test_organization_optional_fields(self, organization):
        """Test organization optional fields."""
        organization.phone = '555-123-4567'
        organization.notes = 'Important client'
        organization.save()
        
        org = Organization.objects.get(pk=organization.pk)
        assert org.phone == '555-123-4567'
        assert org.notes == 'Important client'


class TestContactModel:
    """Tests for the Contact model."""
    
    @pytest.mark.django_db
    def test_create_contact(self, organization):
        """Test creating a contact."""
        contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            organization=organization,
        )
        assert contact.email == 'john.doe@example.com'
        assert contact.organization == organization
    
    @pytest.mark.django_db
    def test_contact_str(self, contact):
        """Test contact string representation."""
        # Should show full name
        assert contact.first_name in str(contact)
        assert contact.last_name in str(contact)
    
    @pytest.mark.django_db
    def test_contact_without_organization(self):
        """Test contact can exist without organization."""
        contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@personal.com',
        )
        assert contact.organization is None


class TestLeadModel:
    """Tests for the Lead model."""
    
    @pytest.mark.django_db
    def test_create_lead(self, contact):
        """Test creating a lead."""
        lead = Lead.objects.create(
            title='New IT Project',
            contact=contact,
            source='website',
            status='new',
        )
        assert lead.title == 'New IT Project'
        assert lead.status == 'new'
    
    @pytest.mark.django_db
    def test_lead_str(self, lead):
        """Test lead string representation."""
        assert lead.title in str(lead)
    
    @pytest.mark.django_db
    def test_lead_status_transitions(self, lead):
        """Test lead can change status."""
        statuses = ['new', 'contacted', 'discovery', 'proposal', 'negotiation', 'won', 'lost']
        for status in statuses:
            lead.status = status
            lead.save()
            lead.refresh_from_db()
            assert lead.status == status
    
    @pytest.mark.django_db
    def test_lead_value(self, lead):
        """Test lead estimated value."""
        lead.estimated_value = Decimal('50000.00')
        lead.save()
        lead.refresh_from_db()
        assert lead.estimated_value == Decimal('50000.00')
    
    @pytest.mark.django_db
    def test_lead_assignment(self, lead, staff_user):
        """Test assigning lead to user."""
        lead.assigned_to = staff_user
        lead.save()
        lead.refresh_from_db()
        assert lead.assigned_to == staff_user
    
    @pytest.mark.django_db
    def test_lead_organization_link(self, lead, organization):
        """Test linking lead to organization."""
        lead.organization = organization
        lead.save()
        lead.refresh_from_db()
        assert lead.organization == organization
    
    @pytest.mark.django_db
    def test_lead_sources(self, contact):
        """Test all valid lead sources."""
        sources = ['website', 'referral', 'cold_call', 'social', 'event', 'partner', 'other']
        for source in sources:
            lead = Lead.objects.create(
                title=f'Lead from {source}',
                contact=contact,
                source=source,
                status='new',
            )
            assert lead.source == source


class TestLeadQualification:
    """Tests for lead qualification logic."""
    
    @pytest.mark.django_db
    def test_qualified_lead_has_value(self, lead):
        """Test that qualified leads should have estimated value."""
        lead.status = 'qualified'
        lead.estimated_value = Decimal('25000.00')
        lead.save()
        
        assert lead.estimated_value > 0
    
    @pytest.mark.django_db
    def test_won_lead_tracking(self, lead):
        """Test marking lead as won."""
        lead.status = 'won'
        lead.save()
        
        won_leads = Lead.objects.filter(status='won')
        assert lead in won_leads
    
    @pytest.mark.django_db
    def test_lost_lead_tracking(self, lead):
        """Test marking lead as lost."""
        lead.status = 'lost'
        lead.save()
        
        lost_leads = Lead.objects.filter(status='lost')
        assert lead in lost_leads


class TestPipelineQuerysets:
    """Tests for pipeline-related querysets."""
    
    @pytest.mark.django_db
    def test_leads_by_status(self, contact):
        """Test filtering leads by status."""
        Lead.objects.create(title='Lead 1', contact=contact, status='new')
        Lead.objects.create(title='Lead 2', contact=contact, status='discovery')
        Lead.objects.create(title='Lead 3', contact=contact, status='new')
        
        new_leads = Lead.objects.filter(status='new')
        discovery_leads = Lead.objects.filter(status='discovery')
        
        assert new_leads.count() >= 2
        assert discovery_leads.count() >= 1
    
    @pytest.mark.django_db
    def test_pipeline_value_calculation(self, contact):
        """Test calculating total pipeline value."""
        Lead.objects.create(
            title='Lead 1', contact=contact,
            status='discovery', estimated_value=Decimal('10000')
        )
        Lead.objects.create(
            title='Lead 2', contact=contact,
            status='proposal', estimated_value=Decimal('20000')
        )
        Lead.objects.create(
            title='Lead 3', contact=contact,
            status='lost', estimated_value=Decimal('5000')
        )
        
        # Pipeline value should exclude lost leads
        active_pipeline = Lead.objects.exclude(status__in=['won', 'lost'])
        from django.db.models import Sum
        total = active_pipeline.aggregate(Sum('estimated_value'))['estimated_value__sum']
        
        assert total == Decimal('30000')
