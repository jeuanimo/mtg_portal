from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Fieldset
from .models import Organization, Contact, Lead, Activity, Task


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'website', 'industry', 'size', 'phone', 'email',
                  'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'notes']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset('Organization Details',
                Row(
                    Column('name', css_class='col-md-6'),
                    Column('website', css_class='col-md-6'),
                ),
                Row(
                    Column('industry', css_class='col-md-4'),
                    Column('size', css_class='col-md-4'),
                    Column('phone', css_class='col-md-4'),
                ),
                'email',
            ),
            Fieldset('Address',
                'address_line1',
                'address_line2',
                Row(
                    Column('city', css_class='col-md-4'),
                    Column('state', css_class='col-md-4'),
                    Column('postal_code', css_class='col-md-4'),
                ),
                'country',
            ),
            'notes',
            Submit('submit', 'Save Organization', css_class='btn-primary')
        )


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['organization', 'first_name', 'last_name', 'email', 'phone', 'job_title', 'is_primary', 'notes']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'organization',
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            Row(
                Column('email', css_class='col-md-6'),
                Column('phone', css_class='col-md-6'),
            ),
            Row(
                Column('job_title', css_class='col-md-6'),
                Column('is_primary', css_class='col-md-6'),
            ),
            'notes',
            Submit('submit', 'Save Contact', css_class='btn-primary')
        )


class LeadForm(forms.ModelForm):
    # Combo fields: allow selecting existing or typing new values
    contact_name = forms.CharField(
        max_length=200, required=True,
        help_text='Type to search existing contacts or enter a new name (First Last)',
        widget=forms.TextInput(attrs={
            'list': 'contact-datalist',
            'autocomplete': 'off',
            'placeholder': 'e.g. John Smith',
        }),
    )
    contact_email = forms.EmailField(
        required=True,
        help_text='Email for new contact, or to match an existing one',
        widget=forms.EmailInput(attrs={
            'list': 'contact-email-datalist',
            'autocomplete': 'off',
            'placeholder': 'e.g. john@example.com',
        }),
    )
    contact_phone = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 555-123-4567'}),
    )
    organization_name = forms.CharField(
        max_length=200, required=False,
        help_text='Type to search existing organizations or enter a new name',
        widget=forms.TextInput(attrs={
            'list': 'organization-datalist',
            'autocomplete': 'off',
            'placeholder': 'e.g. Acme Corp',
        }),
    )

    class Meta:
        model = Lead
        fields = ['title', 'status', 'source', 'priority',
                  'estimated_value', 'probability', 'expected_close_date', 'next_followup',
                  'assigned_to', 'notes', 'lost_reason']
        widgets = {
            'expected_close_date': forms.DateInput(attrs={'type': 'date'}),
            'next_followup': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'lost_reason': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['lost_reason'].required = False

        # Pre-populate combo fields when editing an existing lead
        if self.instance and self.instance.pk:
            if self.instance.contact:
                self.fields['contact_name'].initial = self.instance.contact.full_name
                self.fields['contact_email'].initial = self.instance.contact.email
                self.fields['contact_phone'].initial = self.instance.contact.phone
            if self.instance.organization:
                self.fields['organization_name'].initial = self.instance.organization.name

        self.helper.layout = Layout(
            'title',
            Fieldset('Contact',
                Row(
                    Column('contact_name', css_class='col-md-4'),
                    Column('contact_email', css_class='col-md-4'),
                    Column('contact_phone', css_class='col-md-4'),
                ),
            ),
            Fieldset('Organization',
                'organization_name',
            ),
            Row(
                Column('status', css_class='col-md-4'),
                Column('source', css_class='col-md-4'),
                Column('priority', css_class='col-md-4'),
            ),
            Row(
                Column('estimated_value', css_class='col-md-4'),
                Column('probability', css_class='col-md-4'),
                Column('expected_close_date', css_class='col-md-4'),
            ),
            Row(
                Column('assigned_to', css_class='col-md-6'),
                Column('next_followup', css_class='col-md-6'),
            ),
            'notes',
            'lost_reason',
            Submit('submit', 'Save Lead', css_class='btn-primary')
        )

    def resolve_contact_and_organization(self):
        """Look up or create Contact and Organization from the combo fields."""
        org = None
        org_name = self.cleaned_data.get('organization_name', '').strip()
        if org_name:
            org, _created = Organization.objects.get_or_create(
                name__iexact=org_name,
                defaults={'name': org_name},
            )

        email = self.cleaned_data['contact_email'].strip()
        name_parts = self.cleaned_data['contact_name'].strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        phone = self.cleaned_data.get('contact_phone', '').strip()

        contact, created = Contact.objects.get_or_create(
            email__iexact=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'organization': org,
            },
        )
        # Update existing contact's org if it was blank and user provided one
        if not created and org and not contact.organization:
            contact.organization = org
            contact.save(update_fields=['organization'])

        return contact, org


class LeadStatusForm(forms.ModelForm):
    """Quick form for updating just the lead status."""
    class Meta:
        model = Lead
        fields = ['status', 'lost_reason']
        widgets = {
            'lost_reason': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Reason for losing the lead...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.layout = Layout(
            'status',
            'lost_reason',
            Submit('submit', 'Update Status', css_class='btn-primary')
        )


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['activity_type', 'subject', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('activity_type', css_class='col-md-4'),
                Column('subject', css_class='col-md-8'),
            ),
            'description',
            Submit('submit', 'Add Activity', css_class='btn-primary')
        )


class TaskForm(forms.ModelForm):
    """Form for creating/editing CRM tasks."""
    class Meta:
        model = Task
        fields = ['title', 'description', 'lead', 'contact', 'organization', 
                  'assigned_to', 'priority', 'status', 'due_date']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        lead = kwargs.pop('lead', None)
        contact = kwargs.pop('contact', None)
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        if lead:
            self.fields['lead'].initial = lead
            self.fields['lead'].widget = forms.HiddenInput()
        if contact:
            self.fields['contact'].initial = contact
            self.fields['contact'].widget = forms.HiddenInput()
        if organization:
            self.fields['organization'].initial = organization
            self.fields['organization'].widget = forms.HiddenInput()
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            'description',
            'lead',
            'contact',
            'organization',
            Row(
                Column('assigned_to', css_class='col-md-6'),
                Column('due_date', css_class='col-md-6'),
            ),
            Row(
                Column('priority', css_class='col-md-6'),
                Column('status', css_class='col-md-6'),
            ),
            Submit('submit', 'Save Task', css_class='btn-primary')
        )


class QuickLeadForm(forms.Form):
    """Quick lead intake form for public submissions."""
    name = forms.CharField(max_length=200)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    company = forms.CharField(max_length=200, required=False)
    interest = forms.CharField(max_length=300, widget=forms.Textarea(attrs={'rows': 3}))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='col-md-6'),
                Column('email', css_class='col-md-6'),
            ),
            Row(
                Column('phone', css_class='col-md-6'),
                Column('company', css_class='col-md-6'),
            ),
            'interest',
            Submit('submit', 'Submit Inquiry', css_class='btn-primary btn-lg')
        )
    
    def create_lead(self, source='website'):
        """Create a lead from the form data."""
        # Parse name
        name_parts = self.cleaned_data['name'].split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create or get organization
        organization = None
        if self.cleaned_data.get('company'):
            organization, _ = Organization.objects.get_or_create(
                name=self.cleaned_data['company'],
                defaults={'email': self.cleaned_data['email']}
            )
        
        # Create or get contact
        contact, _ = Contact.objects.get_or_create(
            email=self.cleaned_data['email'],
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': self.cleaned_data.get('phone', ''),
                'organization': organization,
            }
        )
        
        # Create lead
        lead = Lead.objects.create(
            title=self.cleaned_data['interest'][:200],
            contact=contact,
            organization=organization,
            source=source,
            notes=self.cleaned_data['interest'],
        )
        
        return lead
