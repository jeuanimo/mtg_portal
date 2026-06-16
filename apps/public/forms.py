from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
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
        self.fields['phone'].widget.attrs['placeholder'] = 'Your phone number'
        self.fields['company'].widget.attrs['placeholder'] = 'Your Company'
        self.fields['subject'].widget.attrs['placeholder'] = 'How can we help?'
        self.fields['message'].widget.attrs['placeholder'] = 'Tell us about your project or question...'
        self.fields['message'].widget.attrs['rows'] = 5


class ConsultationRequestForm(forms.ModelForm):
    """Consultation request form."""

    WEB_KEYWORDS = (
        'web', 'website', 'frontend', 'front-end', 'ui', 'ux', 'design', 'ecommerce'
    )

    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True).order_by('order', 'title'),
        required=True,
        label='Service Needed',
        empty_label='Select a service...',
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

    website_type = forms.ChoiceField(
        choices=[
            ('', 'Select website type...'),
            ('marketing', 'Marketing / Brochure Site'),
            ('ecommerce', 'E-commerce Store'),
            ('web_app', 'Web Application / Portal'),
            ('landing', 'Landing Page / Campaign Site'),
            ('other', 'Other'),
        ],
        required=False,
        label='Website type',
    )
    target_audience = forms.CharField(
        required=False,
        label='Target audience',
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    ui_style = forms.CharField(
        required=False,
        label='Preferred UI style',
        widget=forms.TextInput(
            attrs={'placeholder': 'Modern, minimal, bold, playful, corporate, etc.'}
        ),
    )
    inspiration_url = forms.URLField(
        required=False,
        label='Inspiration URL',
        widget=forms.URLInput(attrs={'placeholder': 'https://example.com'}),
    )
    preferred_color_scheme = forms.CharField(
        required=False,
        label='Preferred color scheme',
        widget=forms.TextInput(
            attrs={'placeholder': 'Primary, secondary, accent colors or brand palette'}
        ),
    )
    avoid_colors = forms.CharField(
        required=False,
        label='Colors to avoid',
        widget=forms.TextInput(attrs={'placeholder': 'List any colors to avoid'}),
    )
    must_have_features = forms.CharField(
        required=False,
        label='Must-have frontend features',
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    nice_to_have_features = forms.CharField(
        required=False,
        label='Nice-to-have features',
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    content_ready = forms.ChoiceField(
        choices=[
            ('', 'Select content readiness...'),
            ('ready', 'Content is ready'),
            ('partial', 'Content is partially ready'),
            ('need_help', 'Need help creating content'),
        ],
        required=False,
        label='Content readiness',
    )
    accessibility_requirements = forms.CharField(
        required=False,
        label='Accessibility requirements',
        widget=forms.Textarea(attrs={'rows': 2}),
    )
    responsive_priority = forms.ChoiceField(
        choices=[
            ('', 'Select priority...'),
            ('mobile_first', 'Mobile-first'),
            ('balanced', 'Balanced mobile and desktop'),
            ('desktop_first', 'Desktop-first'),
        ],
        required=False,
        label='Responsive design priority',
    )

    class Meta:
        model = ServiceRequest
        fields = [
            'name', 'email', 'phone', 'company',
            'service', 'budget_range', 'timeline',
            'description'
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
                Column('company', css_class='col-md-6'),
            ),
            HTML('<hr class="my-4"><h5 class="mb-3">Project Details</h5>'),
            'service',
            Row(
                Column('budget_range', css_class='col-md-6'),
                Column('timeline', css_class='col-md-6'),
            ),
            HTML('<h5 class="mb-3 mt-4">Preferred Meeting Time</h5>'),
            Row(
                Column('preferred_date', css_class='col-md-6'),
                Column('preferred_time', css_class='col-md-6'),
            ),
            HTML('<hr class="my-4"><h5 class="mb-3">Web Design Discovery</h5>'
                 '<p class="text-muted small">Required when selecting web development-related services.</p>'),
            Row(
                Column('website_type', css_class='col-md-6'),
                Column('content_ready', css_class='col-md-6'),
            ),
            'target_audience',
            Row(
                Column('ui_style', css_class='col-md-6'),
                Column('preferred_color_scheme', css_class='col-md-6'),
            ),
            Row(
                Column('inspiration_url', css_class='col-md-6'),
                Column('avoid_colors', css_class='col-md-6'),
            ),
            Row(
                Column('responsive_priority', css_class='col-md-6'),
                Column('accessibility_requirements', css_class='col-md-6'),
            ),
            'must_have_features',
            'nice_to_have_features',
            'description',
            Submit('submit', 'Request Consultation', css_class='btn-primary btn-lg w-100')
        )

        # Add placeholders and styling
        self.fields['name'].widget.attrs['placeholder'] = 'Your Full Name'
        self.fields['email'].widget.attrs['placeholder'] = 'your@email.com'
        self.fields['phone'].widget.attrs['placeholder'] = 'Your phone number'
        self.fields['company'].widget.attrs['placeholder'] = 'Your Company Name'
        self.fields['description'].widget.attrs['placeholder'] = 'Tell us about your project goals, current challenges, or any specific requirements...'
        self.fields['description'].widget.attrs['rows'] = 4
        self.fields['description'].label = 'Additional Information'

    def _is_web_service(self, service):
        """Return True when selected service indicates web design/development."""
        if not service:
            return False
        haystack = ' '.join([
            service.title or '',
            service.slug or '',
            service.short_description or '',
        ]).lower()
        return any(keyword in haystack for keyword in self.WEB_KEYWORDS)

    def clean(self):
        cleaned_data = super().clean()
        service = cleaned_data.get('service')

        if not self._is_web_service(service):
            return cleaned_data

        required_for_web = {
            'website_type': 'Please choose the website type.',
            'target_audience': 'Please describe your target audience.',
            'ui_style': 'Please describe your preferred UI style.',
            'inspiration_url': 'Please provide at least one inspiration URL.',
            'preferred_color_scheme': 'Please provide your preferred color scheme.',
            'must_have_features': 'Please list required frontend features.',
            'responsive_priority': 'Please select a responsive design priority.',
        }

        for field_name, message in required_for_web.items():
            if not cleaned_data.get(field_name):
                self.add_error(field_name, message)

        return cleaned_data
