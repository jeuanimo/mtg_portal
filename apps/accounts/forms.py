from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import User, UserProfile


class UserAdminEditForm(forms.ModelForm):
    """Staff-facing form to update a portal user's role, org, and basic info."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'role', 'organization', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organization'].required = False
        self.fields['organization'].queryset = self._org_queryset()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            Row(
                Column('phone', css_class='col-md-6'),
                Column('role', css_class='col-md-6'),
            ),
            'organization',
            'is_active',
            Submit('submit', 'Save Changes', css_class='btn-primary'),
        )

    @staticmethod
    def _org_queryset():
        try:
            from apps.crm.models import Organization
            return Organization.objects.all().order_by('name')
        except Exception:
            from django.db.models import QuerySet
            return User.objects.none()


class UserUpdateForm(forms.ModelForm):
    """Form for updating user information."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'company', 'job_title', 'bio', 'avatar']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            Row(
                Column('phone', css_class='col-md-6'),
                Column('company', css_class='col-md-6'),
            ),
            'job_title',
            'bio',
            'avatar',
            Submit('submit', 'Update Profile', css_class='btn-primary')
        )


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile (address, etc.)."""
    
    class Meta:
        model = UserProfile
        fields = ['address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'timezone']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'address_line1',
            'address_line2',
            Row(
                Column('city', css_class='col-md-4'),
                Column('state', css_class='col-md-4'),
                Column('postal_code', css_class='col-md-4'),
            ),
            Row(
                Column('country', css_class='col-md-6'),
                Column('timezone', css_class='col-md-6'),
            ),
            Submit('submit', 'Update Address', css_class='btn-primary')
        )


class NotificationSettingsForm(forms.ModelForm):
    """Form for updating notification preferences."""
    
    class Meta:
        model = User
        fields = ['email_notifications', 'sms_notifications']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Save Settings', css_class='btn-primary'))
