from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Field, Div
from .models import ContactSubmission, ServiceRequest, Service


class ContactForm(forms.ModelForm):
    """Contact form for the public website."""
    
    class Meta:
        model = ContactSubmission
        fields = ['name', 'email', 'phone', 'company', 'subject', 'message']
    
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
            'subject',
            'message',
            Submit('submit', 'Send Message', css_class='btn-primary btn-lg')
        )
        
        # Add placeholders
        self.fields['name'].widget.attrs['placeholder'] = 'Your Name'
        self.fields['email'].widget.attrs['placeholder'] = 'your@email.com'
        self.fields['phone'].widget.attrs['placeholder'] = '(555) 123-4567'
        self.fields['company'].widget.attrs['placeholder'] = 'Your Company'
        self.fields['subject'].widget.attrs['placeholder'] = 'How can we help?'
        self.fields['message'].widget.attrs['placeholder'] = 'Tell us about your project or question...'
        self.fields['message'].widget.attrs['rows'] = 5


class ConsultationRequestForm(forms.ModelForm):
    """Consultation request form."""
    
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Services you\'re interested in'
    )
    
    preferred_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='Preferred consultation date'
    )
    
    preferred_time = forms.ChoiceField(
        choices=[
            ('', 'Select a time...'),
            ('morning', 'Morning (9am - 12pm)'),
            ('afternoon', 'Afternoon (12pm - 5pm)'),
            ('evening', 'Evening (5pm - 7pm)'),
        ],
        required=False,
        label='Preferred time'
    )
    
    class Meta:
        model = ServiceRequest
        fields = [
            'name', 'email', 'phone', 'company_name', 
            'services', 'budget_range', 'timeline',
            'preferred_date', 'preferred_time', 'message'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'consultation-form'
        self.helper.layout = Layout(
            HTML('<h5 class="mb-3">Your Information</h5>'),
            Row(
                Column('name', css_class='col-md-6'),
                Column('email', css_class='col-md-6'),
            ),
            Row(
                Column('phone', css_class='col-md-6'),
                Column('company_name', css_class='col-md-6'),
            ),
            HTML('<hr class="my-4"><h5 class="mb-3">Project Details</h5>'),
            'services',
            Row(
                Column('budget_range', css_class='col-md-6'),
                Column('timeline', css_class='col-md-6'),
            ),
            HTML('<h5 class="mb-3 mt-4">Preferred Meeting Time</h5>'),
            Row(
                Column('preferred_date', css_class='col-md-6'),
                Column('preferred_time', css_class='col-md-6'),
            ),
            'message',
            Submit('submit', 'Request Consultation', css_class='btn-primary btn-lg w-100')
        )
        
        # Add placeholders and styling
        self.fields['name'].widget.attrs['placeholder'] = 'Your Full Name'
        self.fields['email'].widget.attrs['placeholder'] = 'your@email.com'
        self.fields['phone'].widget.attrs['placeholder'] = '(555) 123-4567'
        self.fields['company_name'].widget.attrs['placeholder'] = 'Your Company Name'
        self.fields['message'].widget.attrs['placeholder'] = 'Tell us about your project goals, current challenges, or any specific requirements...'
        self.fields['message'].widget.attrs['rows'] = 4
        self.fields['message'].label = 'Additional Information'
