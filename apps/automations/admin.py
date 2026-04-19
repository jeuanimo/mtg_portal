from django.contrib import admin

from .models import (
    AgentConfig, PromptTemplate, Campaign,
    AgentTask, AgentExecutionLog, CampaignMetric,
)


class PromptTemplateInline(admin.TabularInline):
    model = PromptTemplate
    extra = 0


class AgentTaskInline(admin.TabularInline):
    model = AgentTask
    extra = 0
    fields = ['title', 'content_type', 'status', 'created_at']
    readonly_fields = ['created_at']


class CampaignMetricInline(admin.TabularInline):
    model = CampaignMetric
    extra = 0


@admin.register(AgentConfig)
class AgentConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'agent_type', 'scope', 'model_name', 'is_active', 'organization', 'created_at']
    list_filter = ['agent_type', 'scope', 'is_active']
    search_fields = ['name', 'description']
    inlines = [PromptTemplateInline]


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign_type', 'status', 'agent', 'start_date', 'end_date', 'created_at']
    list_filter = ['campaign_type', 'status']
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    inlines = [AgentTaskInline, CampaignMetricInline]


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'campaign', 'content_type', 'status', 'reviewed_by', 'reviewed_at', 'published_at']
    list_filter = ['status', 'content_type']
    search_fields = ['title', 'generated_content']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AgentExecutionLog)
class AgentExecutionLogAdmin(admin.ModelAdmin):
    list_display = ['agent', 'task', 'model_used', 'input_tokens', 'output_tokens', 'estimated_cost', 'success', 'created_at']
    list_filter = ['success', 'model_used']
    readonly_fields = ['created_at']


@admin.register(CampaignMetric)
class CampaignMetricAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'date', 'platform', 'impressions', 'clicks', 'conversions', 'spend', 'revenue']
    list_filter = ['platform']
    date_hierarchy = 'date'
