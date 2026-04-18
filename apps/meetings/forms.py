from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Fieldset
from apps.core.widgets import DatalistTextInput
from .models import Meeting, MeetingAttendee, AvailabilitySlot


class MeetingForm(forms.ModelForm):
    """Form for creating/editing meetings."""
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date'
    )
    start_time_field = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label='Start Time'
    )
    end_time_field = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label='End Time'
    )
    
    class Meta:
        model = Meeting
        fields = [
            'title', 'meeting_type', 'description', 'agenda',
            'video_provider', 'location',
            'host', 'organization', 'contact', 'project', 'ticket',
            'is_recorded', 'allow_client_join'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'agenda': forms.Textarea(attrs={'rows': 4}),
            'meeting_type': DatalistTextInput(choices=Meeting.MeetingType.choices),
            'video_provider': DatalistTextInput(choices=Meeting.Provider.choices),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Populate date/time fields from existing meeting
        if self.instance.pk:
            self.fields['start_date'].initial = self.instance.start_time.date()
            self.fields['start_time_field'].initial = self.instance.start_time.time()
            self.fields['end_time_field'].initial = self.instance.end_time.time()
        else:
            # Default to tomorrow at 10 AM
            tomorrow = timezone.now() + timezone.timedelta(days=1)
            self.fields['start_date'].initial = tomorrow.date()
            self.fields['start_time_field'].initial = '10:00'
            self.fields['end_time_field'].initial = '11:00'
        
        # Limit hosts to internal users with active portal access.
        from apps.accounts.models import User
        self.fields['host'].queryset = User.internal_users().order_by('first_name', 'last_name', 'email')
        self.fields['host'].required = False
        
        # Organization and contact
        from apps.crm.models import Organization, Contact
        self.fields['organization'].queryset = Organization.objects.order_by('name')
        self.fields['contact'].queryset = Contact.objects.select_related('organization').order_by('last_name', 'first_name')
        
        # Project and ticket
        from apps.tickets.models import ConsultingProject, Ticket
        self.fields['project'].queryset = ConsultingProject.objects.exclude(
            status__in=[ConsultingProject.Status.COMPLETED, ConsultingProject.Status.CANCELLED]
        )
        self.fields['ticket'].queryset = Ticket.objects.filter(
            status__in=Ticket.OPEN_STATUSES
        )
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'title',
            Row(
                Column('meeting_type', css_class='col-md-6'),
                Column('video_provider', css_class='col-md-6'),
            ),
            Row(
                Column('start_date', css_class='col-md-4'),
                Column('start_time_field', css_class='col-md-4'),
                Column('end_time_field', css_class='col-md-4'),
            ),
            'description',
            'agenda',
            Fieldset(
                'Participants',
                Row(
                    Column('host', css_class='col-md-6'),
                    Column('organization', css_class='col-md-6'),
                ),
                'contact',
            ),
            Fieldset(
                'Related Items',
                Row(
                    Column('project', css_class='col-md-6'),
                    Column('ticket', css_class='col-md-6'),
                ),
            ),
            'location',
            Row(
                Column('is_recorded', css_class='col-md-6'),
                Column('allow_client_join', css_class='col-md-6'),
            ),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        start_time = cleaned_data.get('start_time_field')
        end_time = cleaned_data.get('end_time_field')
        
        if start_date and start_time:
            cleaned_data['start_time'] = timezone.make_aware(
                timezone.datetime.combine(start_date, start_time)
            )
        
        if start_date and end_time:
            end_datetime = timezone.datetime.combine(start_date, end_time)
            # Handle meetings that cross midnight
            if end_time <= start_time:
                end_datetime += timezone.timedelta(days=1)
            cleaned_data['end_time'] = timezone.make_aware(end_datetime)
        
        if cleaned_data.get('start_time') and cleaned_data.get('end_time'):
            if cleaned_data['end_time'] <= cleaned_data['start_time']:
                raise forms.ValidationError("End time must be after start time.")
        
        return cleaned_data
    
    def save(self, commit=True):
        meeting = super().save(commit=False)
        meeting.start_time = self.cleaned_data.get('start_time')
        meeting.end_time = self.cleaned_data.get('end_time')
        
        if not meeting.organizer_id and self.user:
            meeting.organizer = self.user
        
        if not meeting.host_id:
            meeting.host = meeting.organizer
        
        if commit:
            meeting.save()
            self.save_m2m()
        return meeting


class QuickMeetingForm(forms.ModelForm):
    """Simplified form for quickly scheduling meetings."""
    
    duration = forms.ChoiceField(
        choices=[
            (15, '15 minutes'),
            (30, '30 minutes'),
            (45, '45 minutes'),
            (60, '1 hour'),
            (90, '1.5 hours'),
            (120, '2 hours'),
        ],
        initial=30
    )
    
    start_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label='When'
    )
    
    class Meta:
        model = Meeting
        fields = ['title', 'meeting_type', 'organization', 'video_provider']
        widgets = {
            'meeting_type': DatalistTextInput(choices=Meeting.MeetingType.choices),
            'video_provider': DatalistTextInput(choices=Meeting.Provider.choices),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from apps.crm.models import Organization
        self.fields['organization'].queryset = Organization.objects.order_by('name')
        self.fields['organization'].required = False
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
    
    def save(self, commit=True):
        meeting = super().save(commit=False)
        meeting.start_time = self.cleaned_data['start_datetime']
        duration = int(self.cleaned_data['duration'])
        meeting.end_time = meeting.start_time + timezone.timedelta(minutes=duration)
        
        if commit:
            meeting.save()
        return meeting


class MeetingNotesForm(forms.ModelForm):
    """Form for updating meeting notes."""
    
    class Meta:
        model = Meeting
        fields = ['notes', 'action_items']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Meeting notes and minutes...'}),
            'action_items': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Follow-up action items...'}),
        }


class MeetingAttendeeForm(forms.ModelForm):
    """Form for adding attendees to a meeting."""
    
    class Meta:
        model = MeetingAttendee
        fields = ['user', 'contact', 'email', 'name']
    
    def __init__(self, *args, **kwargs):
        self.meeting = kwargs.pop('meeting', None)
        super().__init__(*args, **kwargs)
        
        from apps.accounts.models import User
        self.fields['user'].queryset = User.objects.filter(is_active=True)
        self.fields['user'].required = False
        
        from apps.crm.models import Contact
        self.fields['contact'].queryset = Contact.objects.select_related('organization').order_by('last_name', 'first_name')
        self.fields['contact'].required = False
        
        self.fields['email'].required = False
        self.fields['name'].required = False
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
    
    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        contact = cleaned_data.get('contact')
        email = cleaned_data.get('email')
        
        # At least one identifier must be provided
        if not any([user, contact, email]):
            raise forms.ValidationError(
                "Please select a user, contact, or enter an email address."
            )
        
        return cleaned_data
    
    def save(self, commit=True):
        attendee = super().save(commit=False)
        if self.meeting:
            attendee.meeting = self.meeting
        if commit:
            attendee.save()
        return attendee


class AvailabilitySlotForm(forms.ModelForm):
    """Form for availability slots."""
    
    class Meta:
        model = AvailabilitySlot
        fields = ['day_of_week', 'start_time', 'end_time', 'is_active']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('day_of_week', css_class='col-md-4'),
                Column('start_time', css_class='col-md-3'),
                Column('end_time', css_class='col-md-3'),
                Column('is_active', css_class='col-md-2'),
            ),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")
        
        return cleaned_data


class MeetingFilterForm(forms.Form):
    """Form for filtering meetings."""
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Meeting.Status.choices),
        required=False
    )
    meeting_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Meeting.MeetingType.choices),
        required=False
    )
    from_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    to_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search meetings...'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field, forms.ChoiceField) else 'form-control'
