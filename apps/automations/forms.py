from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms

from .models import AgentConfig, AgentTask, Campaign, CampaignMetric


class AgentConfigForm(forms.ModelForm):
    class Meta:
        model = AgentConfig
        fields = [
            'name', 'agent_type', 'scope', 'description',
            'system_prompt', 'model_name', 'temperature', 'max_tokens',
            'organization', 'is_active',
        ]
        widgets = {
            'system_prompt': forms.Textarea(attrs={'rows': 6}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='col-md-6'),
                Column('agent_type', css_class='col-md-3'),
                Column('scope', css_class='col-md-3'),
            ),
            'description',
            'system_prompt',
            Row(
                Column('model_name', css_class='col-md-4'),
                Column('temperature', css_class='col-md-4'),
                Column('max_tokens', css_class='col-md-4'),
            ),
            Row(
                Column('organization', css_class='col-md-8'),
                Column('is_active', css_class='col-md-4 mt-4'),
            ),
            Submit('submit', 'Save Agent', css_class='btn btn-primary'),
        )


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = [
            'name', 'campaign_type', 'status', 'agent', 'description',
            'organization', 'start_date', 'end_date',
            'goal_description', 'target_audience',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'goal_description': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['agent'].queryset = AgentConfig.objects.filter(is_active=True)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='col-md-6'),
                Column('campaign_type', css_class='col-md-3'),
                Column('status', css_class='col-md-3'),
            ),
            Row(
                Column('agent', css_class='col-md-6'),
                Column('organization', css_class='col-md-6'),
            ),
            'description',
            Row(
                Column('start_date', css_class='col-md-6'),
                Column('end_date', css_class='col-md-6'),
            ),
            'target_audience',
            'goal_description',
            Submit('submit', 'Save Campaign', css_class='btn btn-primary'),
        )


class AgentTaskReviewForm(forms.ModelForm):
    """Form for staff to review/edit agent-generated content."""

    class Meta:
        model = AgentTask
        fields = ['edited_content', 'rejection_reason', 'platform', 'publish_url']
        widgets = {
            'edited_content': forms.Textarea(attrs={'rows': 10}),
            'rejection_reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['edited_content'].required = False
        self.fields['rejection_reason'].required = False
        self.fields['platform'].required = False
        self.fields['publish_url'].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False


class CampaignMetricForm(forms.ModelForm):
    class Meta:
        model = CampaignMetric
        fields = [
            'date', 'platform', 'impressions', 'clicks', 'conversions',
            'engagements', 'new_leads', 'new_contacts', 'spend', 'revenue', 'notes',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('date', css_class='col-md-6'),
                Column('platform', css_class='col-md-6'),
            ),
            Row(
                Column('impressions', css_class='col-md-3'),
                Column('clicks', css_class='col-md-3'),
                Column('conversions', css_class='col-md-3'),
                Column('engagements', css_class='col-md-3'),
            ),
            Row(
                Column('new_leads', css_class='col-md-6'),
                Column('new_contacts', css_class='col-md-6'),
            ),
            Row(
                Column('spend', css_class='col-md-6'),
                Column('revenue', css_class='col-md-6'),
            ),
            'notes',
            Submit('submit', 'Save Metric', css_class='btn btn-primary'),
        )
