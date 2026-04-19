from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.decorators import staff_required

from .forms import (
    AgentConfigForm,
    AgentTaskReviewForm,
    CampaignForm,
    CampaignMetricForm,
)
from .models import (
    AgentConfig,
    AgentExecutionLog,
    AgentTask,
    Campaign,
    CampaignMetric,
)


# ---------------------------------------------------------------------------
# Agent Effort Dashboard
# ---------------------------------------------------------------------------

@login_required
@staff_required
def dashboard(request):
    """Agent effort dashboard with overview metrics."""
    now = timezone.now()
    thirty_days_ago = now - timezone.timedelta(days=30)

    # Summary stats
    active_campaigns = Campaign.objects.filter(status=Campaign.Status.ACTIVE).count()
    active_agents = AgentConfig.objects.filter(is_active=True).count()
    tasks_pending_review = AgentTask.objects.filter(status=AgentTask.Status.IN_REVIEW).count()
    tasks_published_30d = AgentTask.objects.filter(
        status=AgentTask.Status.PUBLISHED,
        published_at__gte=thirty_days_ago,
    ).count()

    # Recent tasks needing attention
    review_queue = AgentTask.objects.filter(
        status=AgentTask.Status.IN_REVIEW,
    ).select_related('campaign', 'agent')[:10]

    # Recent execution logs
    recent_logs = AgentExecutionLog.objects.select_related(
        'agent', 'task',
    ).order_by('-created_at')[:10]

    # Cost tracking (30 days)
    cost_stats = AgentExecutionLog.objects.filter(
        created_at__gte=thirty_days_ago,
    ).aggregate(
        total_cost=Sum('estimated_cost'),
        total_input_tokens=Sum('input_tokens'),
        total_output_tokens=Sum('output_tokens'),
        avg_execution_time=Avg('execution_time_ms'),
    )

    # Campaign performance (30 days)
    metric_stats = CampaignMetric.objects.filter(
        date__gte=thirty_days_ago.date(),
    ).aggregate(
        total_impressions=Sum('impressions'),
        total_clicks=Sum('clicks'),
        total_conversions=Sum('conversions'),
        total_spend=Sum('spend'),
        total_revenue=Sum('revenue'),
        total_new_leads=Sum('new_leads'),
    )

    # Recent campaigns
    recent_campaigns = Campaign.objects.select_related('agent').order_by('-created_at')[:5]

    context = {
        'active_campaigns': active_campaigns,
        'active_agents': active_agents,
        'tasks_pending_review': tasks_pending_review,
        'tasks_published_30d': tasks_published_30d,
        'review_queue': review_queue,
        'recent_logs': recent_logs,
        'cost_stats': cost_stats,
        'metric_stats': metric_stats,
        'recent_campaigns': recent_campaigns,
    }
    return render(request, 'automations/dashboard.html', context)


# ---------------------------------------------------------------------------
# Campaign CRUD
# ---------------------------------------------------------------------------

@login_required
@staff_required
def campaign_list(request):
    campaigns = Campaign.objects.select_related('agent', 'organization').annotate(
        task_total=Count('tasks'),
        tasks_published=Count('tasks', filter=Q(tasks__status=AgentTask.Status.PUBLISHED)),
    )

    status_filter = request.GET.get('status')
    if status_filter:
        campaigns = campaigns.filter(status=status_filter)

    return render(request, 'automations/campaign_list.html', {
        'campaigns': campaigns,
        'status_choices': Campaign.Status.choices,
        'current_status': status_filter,
    })


@login_required
@staff_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(
        Campaign.objects.select_related('agent', 'organization', 'created_by'), pk=pk,
    )
    tasks = campaign.tasks.select_related('agent').order_by('-created_at')
    metrics = campaign.metrics.order_by('-date')[:30]

    return render(request, 'automations/campaign_detail.html', {
        'campaign': campaign,
        'tasks': tasks,
        'metrics': metrics,
    })


@login_required
@staff_required
def campaign_create(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            messages.success(request, f'Campaign "{campaign.name}" created.')
            return redirect('automations:campaign_detail', pk=campaign.pk)
    else:
        form = CampaignForm()
    return render(request, 'automations/campaign_form.html', {'form': form})


@login_required
@staff_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, f'Campaign "{campaign.name}" updated.')
            return redirect('automations:campaign_detail', pk=campaign.pk)
    else:
        form = CampaignForm(instance=campaign)
    return render(request, 'automations/campaign_form.html', {'form': form, 'campaign': campaign})


# ---------------------------------------------------------------------------
# Agent Config CRUD
# ---------------------------------------------------------------------------

@login_required
@staff_required
def agent_list(request):
    agents = AgentConfig.objects.select_related('organization').annotate(
        campaign_count=Count('campaigns'),
        task_count=Count('tasks'),
    )
    scope_filter = request.GET.get('scope')
    if scope_filter:
        agents = agents.filter(scope=scope_filter)

    return render(request, 'automations/agent_list.html', {
        'agents': agents,
        'scope_choices': AgentConfig.Scope.choices,
        'current_scope': scope_filter,
    })


@login_required
@staff_required
def agent_create(request):
    if request.method == 'POST':
        form = AgentConfigForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            agent.created_by = request.user
            agent.save()
            messages.success(request, f'Agent "{agent.name}" created.')
            return redirect('automations:agent_list')
    else:
        form = AgentConfigForm()
    return render(request, 'automations/agent_form.html', {'form': form})


@login_required
@staff_required
def agent_edit(request, pk):
    agent = get_object_or_404(AgentConfig, pk=pk)
    if request.method == 'POST':
        form = AgentConfigForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            messages.success(request, f'Agent "{agent.name}" updated.')
            return redirect('automations:agent_list')
    else:
        form = AgentConfigForm(instance=agent)
    return render(request, 'automations/agent_form.html', {'form': form, 'agent': agent})


# ---------------------------------------------------------------------------
# Approval Queue
# ---------------------------------------------------------------------------

@login_required
@staff_required
def approval_queue(request):
    """Tasks awaiting staff review/approval."""
    tasks = AgentTask.objects.filter(
        status=AgentTask.Status.IN_REVIEW,
    ).select_related('campaign', 'agent').order_by('-created_at')

    return render(request, 'automations/approval_queue.html', {'tasks': tasks})


@login_required
@staff_required
def task_detail(request, pk):
    task = get_object_or_404(
        AgentTask.objects.select_related('campaign', 'agent', 'reviewed_by'), pk=pk,
    )
    logs = task.execution_logs.order_by('-created_at')

    return render(request, 'automations/task_detail.html', {
        'task': task,
        'logs': logs,
    })


@login_required
@staff_required
def task_review(request, pk):
    """Approve, reject, or edit a task."""
    task = get_object_or_404(AgentTask, pk=pk)
    if request.method == 'POST':
        form = AgentTaskReviewForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            action = request.POST.get('action')
            if action == 'approve':
                task.status = AgentTask.Status.APPROVED
                task.reviewed_by = request.user
                task.reviewed_at = timezone.now()
                messages.success(request, 'Task approved.')
            elif action == 'reject':
                task.status = AgentTask.Status.REJECTED
                task.reviewed_by = request.user
                task.reviewed_at = timezone.now()
                messages.warning(request, 'Task rejected.')
            elif action == 'publish':
                task.status = AgentTask.Status.PUBLISHED
                task.published_at = timezone.now()
                messages.success(request, 'Task published.')
            task.save()
            return redirect('automations:task_detail', pk=task.pk)
    else:
        form = AgentTaskReviewForm(instance=task)
    return render(request, 'automations/task_review.html', {'form': form, 'task': task})


# ---------------------------------------------------------------------------
# Campaign Metrics
# ---------------------------------------------------------------------------

@login_required
@staff_required
def metric_add(request, campaign_pk):
    campaign = get_object_or_404(Campaign, pk=campaign_pk)
    if request.method == 'POST':
        form = CampaignMetricForm(request.POST)
        if form.is_valid():
            metric = form.save(commit=False)
            metric.campaign = campaign
            metric.save()
            messages.success(request, 'Metric recorded.')
            return redirect('automations:campaign_detail', pk=campaign.pk)
    else:
        form = CampaignMetricForm(initial={'date': timezone.now().date()})
    return render(request, 'automations/metric_form.html', {
        'form': form,
        'campaign': campaign,
    })
