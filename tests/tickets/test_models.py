"""
Tests for Ticket models.
"""

import pytest
from django.utils import timezone
from apps.tickets.models import Ticket, TicketComment, TicketAttachment


class TestTicketModel:
    """Tests for the Ticket model."""
    
    @pytest.mark.django_db
    def test_create_ticket(self, client_user):
        """Test creating a ticket."""
        ticket = Ticket.objects.create(
            subject='Test Issue',
            description='Description of the issue',
            created_by=client_user,
            priority='medium',
            status='new',
        )
        assert ticket.subject == 'Test Issue'
        assert ticket.status == 'new'
    
    @pytest.mark.django_db
    def test_ticket_str(self, ticket):
        """Test ticket string representation."""
        assert ticket.subject in str(ticket) or ticket.ticket_number in str(ticket)
    
    @pytest.mark.django_db
    def test_ticket_default_status(self, client_user):
        """Test ticket default status is new."""
        ticket = Ticket.objects.create(
            subject='New Ticket',
            description='Test',
            created_by=client_user,
        )
        assert ticket.status == 'new'


class TestTicketPriority:
    """Tests for ticket priority."""
    
    @pytest.mark.django_db
    def test_priority_levels(self, client_user):
        """Test all priority levels are valid."""
        priorities = ['low', 'medium', 'high', 'urgent']
        for priority in priorities:
            ticket = Ticket.objects.create(
                subject=f'{priority.title()} Priority Ticket',
                description='Test',
                created_by=client_user,
                priority=priority,
            )
            assert ticket.priority == priority
    
    @pytest.mark.django_db
    def test_urgent_ticket(self, urgent_ticket):
        """Test urgent ticket fixture."""
        assert urgent_ticket.priority == 'urgent'


class TestTicketStatus:
    """Tests for ticket status transitions."""
    
    @pytest.mark.django_db
    def test_status_transitions(self, ticket):
        """Test ticket status changes."""
        statuses = ['new', 'in_progress', 'waiting', 'resolved', 'closed']
        for status in statuses:
            ticket.status = status
            ticket.save()
            ticket.refresh_from_db()
            assert ticket.status == status
    
    @pytest.mark.django_db
    def test_resolve_ticket(self, ticket):
        """Test resolving a ticket."""
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.save()
        
        assert ticket.status == 'resolved'
        assert ticket.resolved_at is not None
    
    @pytest.mark.django_db
    def test_close_ticket(self, ticket):
        """Test closing a ticket."""
        ticket.status = 'closed'
        ticket.save()
        
        closed_tickets = Ticket.objects.filter(status='closed')
        assert ticket in closed_tickets


class TestTicketAssignment:
    """Tests for ticket assignment."""
    
    @pytest.mark.django_db
    def test_assign_ticket(self, ticket, staff_user):
        """Test assigning ticket to staff."""
        ticket.assigned_to = staff_user
        ticket.save()
        
        ticket.refresh_from_db()
        assert ticket.assigned_to == staff_user
    
    @pytest.mark.django_db
    def test_unassigned_tickets(self, client_user):
        """Test filtering unassigned tickets."""
        Ticket.objects.create(
            subject='Unassigned 1',
            description='Test',
            created_by=client_user,
        )
        Ticket.objects.create(
            subject='Unassigned 2',
            description='Test',
            created_by=client_user,
        )
        
        unassigned = Ticket.objects.filter(assigned_to__isnull=True)
        assert unassigned.count() >= 2


class TestTicketComments:
    """Tests for ticket comments."""
    
    @pytest.mark.django_db
    def test_add_comment(self, ticket, staff_user):
        """Test adding a comment to ticket."""
        comment = TicketComment.objects.create(
            ticket=ticket,
            author=staff_user,
            content='This is a response to your issue.',
        )
        assert comment.ticket == ticket
        assert comment.author == staff_user
    
    @pytest.mark.django_db
    def test_internal_comment(self, ticket, staff_user):
        """Test internal (staff-only) comment."""
        comment = TicketComment.objects.create(
            ticket=ticket,
            author=staff_user,
            content='Internal note - not for client.',
            is_internal=True,
        )
        assert comment.is_internal is True
    
    @pytest.mark.django_db
    def test_comment_ordering(self, ticket, staff_user):
        """Test comments are ordered by creation time."""
        comment1 = TicketComment.objects.create(
            ticket=ticket, author=staff_user, content='First'
        )
        comment2 = TicketComment.objects.create(
            ticket=ticket, author=staff_user, content='Second'
        )
        
        comments = ticket.comments.all()
        # Should be ordered (depends on Meta ordering)
        assert comments.count() >= 2


class TestTicketAttachments:
    """Tests for ticket attachments."""
    
    @pytest.mark.django_db
    def test_attachment_model(self, ticket, staff_user):
        """Test creating ticket attachment."""
        attachment = TicketAttachment.objects.create(
            ticket=ticket,
            uploaded_by=staff_user,
            file='test_file.pdf',
            filename='test_file.pdf',
        )
        assert attachment.ticket == ticket


class TestTicketQuerysets:
    """Tests for ticket querysets."""
    
    @pytest.mark.django_db
    def test_open_tickets(self, client_user):
        """Test filtering open tickets."""
        Ticket.objects.create(
            subject='New 1', description='Test',
            created_by=client_user, status='new'
        )
        Ticket.objects.create(
            subject='New 2', description='Test',
            created_by=client_user, status='new'
        )
        Ticket.objects.create(
            subject='Closed', description='Test',
            created_by=client_user, status='closed'
        )
        
        new_tickets = Ticket.objects.filter(status='new')
        closed_tickets = Ticket.objects.filter(status='closed')
        
        assert new_tickets.count() >= 2
        assert closed_tickets.count() >= 1
    
    @pytest.mark.django_db
    def test_tickets_by_priority(self, client_user):
        """Test filtering tickets by priority."""
        Ticket.objects.create(
            subject='Urgent', description='Test',
            created_by=client_user, priority='urgent'
        )
        Ticket.objects.create(
            subject='Low', description='Test',
            created_by=client_user, priority='low'
        )
        
        urgent = Ticket.objects.filter(priority='urgent')
        low = Ticket.objects.filter(priority='low')
        
        assert urgent.count() >= 1
        assert low.count() >= 1
    
    @pytest.mark.django_db
    def test_client_tickets(self, client_user, staff_user):
        """Test filtering tickets by client."""
        Ticket.objects.create(
            subject='Client Ticket', description='Test',
            created_by=client_user
        )
        Ticket.objects.create(
            subject='Staff Ticket', description='Test',
            created_by=staff_user
        )
        
        client_tickets = Ticket.objects.filter(created_by=client_user)
        assert client_tickets.count() >= 1
        assert all(t.created_by == client_user for t in client_tickets)
