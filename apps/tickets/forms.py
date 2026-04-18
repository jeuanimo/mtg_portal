"""
Forms for the tickets app.
"""
from django import forms
from django.forms import inlineformset_factory

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML, Submit

from apps.crm.models import Contact
from .models import (
    Ticket, TicketComment, TicketAttachment,
    ConsultingProject, ProjectMilestone, Deliverable,
    ChangeRequest, TimeEntry
)


class TicketForm(forms.ModelForm):
    """Form for creating/editing tickets."""
    
    class Meta:
        model = Ticket
        fields = [
            'subject', 'description', 'category', 'priority',
            'organization', 'contact',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # For clients, pre-fill organization and limit contacts
        if self.user and hasattr(self.user, 'organization') and self.user.organization:
            self.fields['organization'].initial = self.user.organization
            self.fields['organization'].widget = forms.HiddenInput()
            self.fields['contact'].queryset = Contact.objects.filter(
                organization=self.user.organization
            )
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'subject',
            'description',
            Row(
                Column('category', css_class='col-md-6'),
                Column('priority', css_class='col-md-6'),
            ),
            Row(
                Column('organization', css_class='col-md-6'),
                Column('contact', css_class='col-md-6'),
            ),
            Submit('submit', 'Submit Ticket', css_class='btn btn-primary'),
        )


class TicketStaffForm(forms.ModelForm):
    """Extended form for staff to manage tickets."""
    
    class Meta:
        model = Ticket
        fields = [
            'subject', 'description', 'category', 'priority', 'status',
            'organization', 'contact', 'assigned_to', 'due_date', 'project',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from apps.accounts.models import User
        self.fields['assigned_to'].queryset = User.objects.filter(
            role__in=[User.Role.SUPER_ADMIN, User.Role.CONSULTANT, User.Role.STAFF]
        )
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'subject',
            'description',
            Row(
                Column('category', css_class='col-md-4'),
                Column('priority', css_class='col-md-4'),
                Column('status', css_class='col-md-4'),
            ),
            Row(
                Column('organization', css_class='col-md-6'),
                Column('contact', css_class='col-md-6'),
            ),
            Row(
                Column('assigned_to', css_class='col-md-4'),
                Column('due_date', css_class='col-md-4'),
                Column('project', css_class='col-md-4'),
            ),
            Submit('submit', 'Save Ticket', css_class='btn btn-primary'),
        )


class TicketCommentForm(forms.ModelForm):
    """Form for adding comments to tickets."""
    
    class Meta:
        model = TicketComment
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add a comment...',
            }),
        }
    
    def __init__(self, *args, is_staff=False, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only staff can add internal notes
        if not is_staff:
            self.fields.pop('is_internal', None)


class TicketAttachmentForm(forms.ModelForm):
    """Form for uploading attachments."""
    
    class Meta:
        model = TicketAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }


class TicketFilterForm(forms.Form):
    """Form for filtering tickets."""
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Ticket.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    priority = forms.ChoiceField(
        choices=[('', 'All Priorities')] + list(Ticket.Priority.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    category = forms.ChoiceField(
        choices=[('', 'All Categories')] + list(Ticket.Category.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    assigned_to = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label='All Assignees',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search tickets...',
        }),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User
        self.fields['assigned_to'].queryset = User.objects.filter(
            role__in=[User.Role.SUPER_ADMIN, User.Role.CONSULTANT, User.Role.STAFF]
        )


class QuickTicketStatusForm(forms.ModelForm):
    """Quick status update form."""
    
    class Meta:
        model = Ticket
        fields = ['status', 'assigned_to']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User
        self.fields['assigned_to'].queryset = User.objects.filter(
            role__in=[User.Role.SUPER_ADMIN, User.Role.CONSULTANT, User.Role.STAFF]
        )


# Consulting Project Forms

class ConsultingProjectForm(forms.ModelForm):
    """Form for creating/editing consulting projects."""
    
    class Meta:
        model = ConsultingProject
        fields = [
            'name', 'description', 'project_type', 'status',
            'organization', 'primary_contact', 'project_manager',
            'start_date', 'target_end_date', 'actual_end_date',
            'estimated_hours', 'actual_hours', 'budget',
            'team_members',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'target_end_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_end_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from apps.accounts.models import User
        self.fields['project_manager'].queryset = User.objects.filter(
            role__in=[User.Role.SUPER_ADMIN, User.Role.CONSULTANT]
        )
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'description',
            Row(
                Column('project_type', css_class='col-md-6'),
                Column('status', css_class='col-md-6'),
            ),
            Row(
                Column('organization', css_class='col-md-6'),
                Column('primary_contact', css_class='col-md-6'),
            ),
            Row(
                Column('project_manager', css_class='col-md-4'),
                Column('start_date', css_class='col-md-4'),
                Column('target_end_date', css_class='col-md-4'),
            ),
            Row(
                Column('estimated_hours', css_class='col-md-6'),
                Column('budget', css_class='col-md-6'),
            ),
            Submit('submit', 'Save Project', css_class='btn btn-primary'),
        )


class ProjectIntakeForm(forms.Form):
    """Project intake questionnaire form."""
    
    # Business information
    business_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Describe your business',
    )
    industry = forms.CharField(max_length=100)
    company_size = forms.ChoiceField(choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-500', '201-500 employees'),
        ('500+', '500+ employees'),
    ])
    
    # Project requirements
    project_goals = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='What are your project goals?',
    )
    current_challenges = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='What challenges are you facing?',
    )
    success_criteria = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='How will you measure success?',
    )
    
    # Technical requirements
    existing_systems = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        label='Current systems/technology in use',
        required=False,
    )
    integration_needs = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        label='Integration requirements',
        required=False,
    )
    
    # Timeline and budget
    preferred_start = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Preferred start date',
        required=False,
    )
    deadline = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Deadline (if any)',
        required=False,
    )
    budget_range = forms.ChoiceField(choices=[
        ('', 'Select budget range'),
        ('under_5k', 'Under $5,000'),
        ('5k_15k', '$5,000 - $15,000'),
        ('15k_50k', '$15,000 - $50,000'),
        ('50k_100k', '$50,000 - $100,000'),
        ('100k_plus', '$100,000+'),
        ('not_sure', 'Not sure'),
    ])
    
    # Additional info
    additional_info = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Any additional information?',
        required=False,
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5 class="mb-3">Business Information</h5>'),
            'business_description',
            Row(
                Column('industry', css_class='col-md-6'),
                Column('company_size', css_class='col-md-6'),
            ),
            HTML('<hr><h5 class="mb-3">Project Requirements</h5>'),
            'project_goals',
            'current_challenges',
            'success_criteria',
            HTML('<hr><h5 class="mb-3">Technical Details</h5>'),
            'existing_systems',
            'integration_needs',
            HTML('<hr><h5 class="mb-3">Timeline & Budget</h5>'),
            Row(
                Column('preferred_start', css_class='col-md-4'),
                Column('deadline', css_class='col-md-4'),
                Column('budget_range', css_class='col-md-4'),
            ),
            'additional_info',
            Submit('submit', 'Submit Intake Form', css_class='btn btn-primary btn-lg'),
        )


class MilestoneForm(forms.ModelForm):
    """Form for project milestones."""
    
    class Meta:
        model = ProjectMilestone
        fields = ['name', 'description', 'due_date', 'status', 'order']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


MilestoneFormSet = inlineformset_factory(
    ConsultingProject,
    ProjectMilestone,
    form=MilestoneForm,
    extra=2,
    can_delete=True,
)


class DeliverableForm(forms.ModelForm):
    """Form for deliverables."""
    
    class Meta:
        model = Deliverable
        fields = ['name', 'description', 'milestone', 'due_date', 'status', 'file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ChangeRequestForm(forms.ModelForm):
    """Form for change requests."""
    
    class Meta:
        model = ChangeRequest
        fields = [
            'title', 'description', 'reason',
            'scope_impact', 'budget_impact', 'schedule_impact_days',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            'description',
            'reason',
            Row(
                Column('scope_impact', css_class='col-md-4'),
                Column('budget_impact', css_class='col-md-4'),
                Column('schedule_impact_days', css_class='col-md-4'),
            ),
            Submit('submit', 'Submit Change Request', css_class='btn btn-primary'),
        )


class TimeEntryForm(forms.ModelForm):
    """Form for time tracking."""
    
    class Meta:
        model = TimeEntry
        fields = ['project', 'ticket', 'date', 'hours', 'description', 'billable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter projects to active ones
        self.fields['project'].queryset = ConsultingProject.objects.filter(
            status__in=[ConsultingProject.Status.IN_PROGRESS, ConsultingProject.Status.DISCOVERY]
        )
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('project', css_class='col-md-6'),
                Column('ticket', css_class='col-md-6'),
            ),
            Row(
                Column('date', css_class='col-md-4'),
                Column('hours', css_class='col-md-4'),
                Column('billable', css_class='col-md-4 pt-4'),
            ),
            'description',
            Submit('submit', 'Log Time', css_class='btn btn-primary'),
        )
