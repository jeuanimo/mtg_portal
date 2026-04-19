"""
Models for the automations app.

Two-fold agent system:
1. Internal MTG agents - marketing, social media, client support for MTG itself
2. Client agents - reusable agent platform for client web applications
"""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.crm.models import Organization


class AgentConfig(TimeStampedModel):
    """Configurable AI agent definition."""

    class AgentType(models.TextChoices):
        MARKETING = 'marketing', 'Marketing Content'
        SOCIAL_MEDIA = 'social_media', 'Social Media'
        CLIENT_SUPPORT = 'client_support', 'Client Support'
        EMAIL_OUTREACH = 'email_outreach', 'Email Outreach'
        SEO = 'seo', 'SEO Optimization'
        CUSTOM = 'custom', 'Custom'

    class Scope(models.TextChoices):
        INTERNAL = 'internal', 'MTG Internal'
        CLIENT = 'client', 'Client Application'

    name = models.CharField(max_length=200)
    agent_type = models.CharField(max_length=30, choices=AgentType.choices)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.INTERNAL)
    description = models.TextField(blank=True)
    system_prompt = models.TextField(help_text='System prompt that defines agent behavior')
    model_name = models.CharField(
        max_length=100, default='gpt-4o',
        help_text='LLM model identifier (e.g. gpt-4o, claude-sonnet-4)',
    )
    temperature = models.FloatField(default=0.7)
    max_tokens = models.PositiveIntegerField(default=2000)

    # Ownership
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, null=True, blank=True,
        related_name='agents', help_text='Client org (null = MTG internal)',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_agents',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_scope_display()})"


class PromptTemplate(TimeStampedModel):
    """Reusable prompt templates for agents."""

    name = models.CharField(max_length=200)
    agent = models.ForeignKey(
        AgentConfig, on_delete=models.CASCADE, related_name='templates',
    )
    template_text = models.TextField(
        help_text='Use {variable_name} for dynamic substitution',
    )
    variables = models.JSONField(
        default=list, blank=True,
        help_text='List of variable names expected in the template',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['agent', 'name']

    def __str__(self):
        return f"{self.agent.name} - {self.name}"


class Campaign(TimeStampedModel):
    """Marketing or outreach campaign grouping agent tasks."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        ARCHIVED = 'archived', 'Archived'

    class CampaignType(models.TextChoices):
        MARKETING = 'marketing', 'Marketing'
        SOCIAL_MEDIA = 'social_media', 'Social Media'
        EMAIL = 'email', 'Email Outreach'
        SUPPORT = 'support', 'Support Automation'
        MIXED = 'mixed', 'Mixed'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    campaign_type = models.CharField(max_length=30, choices=CampaignType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    agent = models.ForeignKey(
        AgentConfig, on_delete=models.SET_NULL, null=True, related_name='campaigns',
    )

    # Scope
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, null=True, blank=True,
        related_name='campaigns', help_text='Client org (null = MTG internal)',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_campaigns',
    )

    # Schedule
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Goals
    goal_description = models.TextField(blank=True)
    target_audience = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def approved_count(self):
        return self.tasks.filter(status=AgentTask.Status.APPROVED).count()

    @property
    def published_count(self):
        return self.tasks.filter(status=AgentTask.Status.PUBLISHED).count()

    @property
    def completion_rate(self):
        total = self.task_count
        if total:
            return round(self.published_count / total * 100)
        return 0


class AgentTask(TimeStampedModel):
    """Individual task/content generated by an agent with approval workflow."""

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        GENERATING = 'generating', 'Generating'
        DRAFT = 'draft', 'Draft'
        IN_REVIEW = 'in_review', 'In Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        PUBLISHED = 'published', 'Published'
        FAILED = 'failed', 'Failed'

    class ContentType(models.TextChoices):
        BLOG_POST = 'blog_post', 'Blog Post'
        SOCIAL_POST = 'social_post', 'Social Media Post'
        EMAIL_DRAFT = 'email_draft', 'Email Draft'
        SUPPORT_REPLY = 'support_reply', 'Support Reply'
        AD_COPY = 'ad_copy', 'Ad Copy'
        SEO_CONTENT = 'seo_content', 'SEO Content'
        CUSTOM = 'custom', 'Custom'

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name='tasks',
    )
    agent = models.ForeignKey(
        AgentConfig, on_delete=models.SET_NULL, null=True, related_name='tasks',
    )
    prompt_template = models.ForeignKey(
        PromptTemplate, on_delete=models.SET_NULL, null=True, blank=True,
    )

    # Task details
    title = models.CharField(max_length=300)
    content_type = models.CharField(max_length=30, choices=ContentType.choices)
    prompt_used = models.TextField(blank=True, help_text='Final resolved prompt sent to LLM')
    generated_content = models.TextField(blank=True, help_text='Raw agent output')
    edited_content = models.TextField(blank=True, help_text='Staff-edited version (if modified)')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)

    # Approval workflow
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_agent_tasks',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Publishing
    published_at = models.DateTimeField(null=True, blank=True)
    publish_url = models.URLField(blank=True, help_text='URL where content was published')
    platform = models.CharField(max_length=100, blank=True, help_text='e.g. LinkedIn, Twitter, Blog')

    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def final_content(self):
        """Return edited content if available, otherwise generated."""
        return self.edited_content or self.generated_content


class AgentExecutionLog(TimeStampedModel):
    """Track every agent execution for monitoring and cost tracking."""

    task = models.ForeignKey(
        AgentTask, on_delete=models.CASCADE, related_name='execution_logs',
    )
    agent = models.ForeignKey(
        AgentConfig, on_delete=models.SET_NULL, null=True,
    )

    # Execution details
    prompt_sent = models.TextField()
    response_received = models.TextField(blank=True)
    model_used = models.CharField(max_length=100)

    # Metrics
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    execution_time_ms = models.PositiveIntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = "OK" if self.success else "FAIL"
        return f"{self.agent} - {status} - {self.created_at:%Y-%m-%d %H:%M}"


class CampaignMetric(TimeStampedModel):
    """Track campaign performance results."""

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name='metrics',
    )
    date = models.DateField()

    # Engagement metrics
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    engagements = models.PositiveIntegerField(default=0)

    # Reach
    new_leads = models.PositiveIntegerField(default=0)
    new_contacts = models.PositiveIntegerField(default=0)

    # Financial
    spend = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Platform breakdown
    platform = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['campaign', 'date', 'platform']

    def __str__(self):
        return f"{self.campaign.name} - {self.date} - {self.platform or 'All'}"

    @property
    def ctr(self):
        """Click-through rate."""
        if self.impressions:
            return round(self.clicks / self.impressions * 100, 2)
        return 0

    @property
    def conversion_rate(self):
        if self.clicks:
            return round(self.conversions / self.clicks * 100, 2)
        return 0

    @property
    def roi(self):
        if self.spend:
            return round((self.revenue - self.spend) / self.spend * 100, 2)
        return 0
