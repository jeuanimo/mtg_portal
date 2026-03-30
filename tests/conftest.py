"""
Pytest configuration and shared fixtures for MTG Portal tests.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.crm.models import Organization, Contact, Lead
from apps.invoicing.models import Invoice, InvoiceItem
from apps.tickets.models import Ticket

User = get_user_model()


# =====================================================
# User Fixtures
# =====================================================

@pytest.fixture
def password():
    """Standard test password."""
    return 'TestPassword123!'


@pytest.fixture
def admin_user(db, password):
    """Create an admin user."""
    user = User.objects.create_user(
        email='admin@test.com',
        password=password,
        first_name='Admin',
        last_name='User',
        role='admin',
        is_staff=True,
        is_superuser=True,
    )
    return user


@pytest.fixture
def staff_user(db, password):
    """Create a staff user."""
    user = User.objects.create_user(
        email='staff@test.com',
        password=password,
        first_name='Staff',
        last_name='User',
        role='staff',
        is_staff=True,
    )
    return user


@pytest.fixture
def consultant_user(db, password):
    """Create a consultant user."""
    user = User.objects.create_user(
        email='consultant@test.com',
        password=password,
        first_name='Consultant',
        last_name='User',
        role='consultant',
        is_staff=True,
    )
    return user


@pytest.fixture
def finance_user(db, password):
    """Create a finance user."""
    user = User.objects.create_user(
        email='finance@test.com',
        password=password,
        first_name='Finance',
        last_name='User',
        role='finance',
        is_staff=True,
    )
    return user


@pytest.fixture
def client_user(db, password):
    """Create a client (non-staff) user."""
    user = User.objects.create_user(
        email='client@test.com',
        password=password,
        first_name='Client',
        last_name='User',
        role='client',
        is_staff=False,
    )
    return user


@pytest.fixture
def authenticated_client(client, staff_user, password):
    """Return a client logged in as staff user."""
    client.login(email=staff_user.email, password=password)
    return client


@pytest.fixture
def admin_client(client, admin_user, password):
    """Return a client logged in as admin user."""
    client.login(email=admin_user.email, password=password)
    return client


@pytest.fixture
def client_user_client(client, client_user, password):
    """Return a client logged in as client user."""
    client.login(email=client_user.email, password=password)
    return client


# =====================================================
# CRM Fixtures
# =====================================================

@pytest.fixture
def organization(db):
    """Create a test organization."""
    return Organization.objects.create(
        name='Test Company',
        email='info@testcompany.com',
        phone='555-123-4567',
        website='https://testcompany.com',
        address='123 Test St',
        city='Test City',
        state='TX',
        zip_code='75001',
    )


@pytest.fixture
def contact(db, organization):
    """Create a test contact."""
    return Contact.objects.create(
        organization=organization,
        first_name='John',
        last_name='Doe',
        email='john.doe@testcompany.com',
        phone='555-123-4568',
        title='CEO',
        is_primary=True,
    )


@pytest.fixture
def lead(db, contact, organization, staff_user):
    """Create a test lead."""
    return Lead.objects.create(
        title='New Software Project',
        contact=contact,
        organization=organization,
        assigned_to=staff_user,
        source='website',
        status='new',
        estimated_value=50000.00,
        notes='Test lead for a software development project.',
    )


# =====================================================
# Invoice Fixtures
# =====================================================

@pytest.fixture
def invoice(db, organization, contact):
    """Create a test invoice."""
    from datetime import date, timedelta
    inv = Invoice.objects.create(
        invoice_number='INV-TEST-001',
        organization=organization,
        contact=contact,
        status='draft',
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=1000.00,
        tax_rate=8.25,
        tax_amount=82.50,
        total=1082.50,
        balance_due=1082.50,
    )
    return inv


@pytest.fixture
def invoice_with_items(invoice):
    """Create an invoice with line items."""
    InvoiceItem.objects.create(
        invoice=invoice,
        description='Web Development Services',
        quantity=10,
        unit_price=100.00,
        line_total=1000.00,
    )
    invoice.calculate_totals()
    return invoice


# =====================================================
# Ticket Fixtures
# =====================================================

@pytest.fixture
def ticket(db, client_user):
    """Create a test ticket."""
    return Ticket.objects.create(
        subject='Test Support Issue',
        description='Description of the test support issue.',
        created_by=client_user,
        priority='medium',
        status='new',
        category='general',
    )


@pytest.fixture
def urgent_ticket(db, client_user):
    """Create an urgent ticket."""
    return Ticket.objects.create(
        subject='Urgent System Down',
        description='Critical system is not responding.',
        created_by=client_user,
        priority='urgent',
        status='new',
        category='technical',
    )



# =====================================================
# Ticket Fixtures
# =====================================================

@pytest.fixture
def ticket(db, client_user, organization):
    """Create a test ticket."""
    return Ticket.objects.create(
        subject='Test Support Ticket',
        description='This is a test ticket that needs resolution.',
        organization=organization,
        created_by=client_user,
        priority='MEDIUM',
        status='OPEN',
        category='SUPPORT',
    )


@pytest.fixture
def urgent_ticket(db, client_user, organization, consultant_user):
    """Create an urgent ticket assigned to consultant."""
    return Ticket.objects.create(
        subject='Urgent System Down',
        description='Production system is not responding.',
        organization=organization,
        created_by=client_user,
        assigned_to=consultant_user,
        priority='URGENT',
        status='IN_PROGRESS',
        category='SUPPORT',
    )
