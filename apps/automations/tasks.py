"""
Celery task scaffolds for agent execution.

These are stubs — actual LLM integration will be added
when API keys and provider SDKs are configured.
"""
import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def execute_agent_task(self, task_id):
    """Execute a single agent task — generate content via LLM."""
    from .models import AgentExecutionLog, AgentTask

    try:
        task = AgentTask.objects.select_related('agent', 'prompt_template').get(pk=task_id)
    except AgentTask.DoesNotExist:
        logger.error("AgentTask %s not found", task_id)
        return

    task.status = AgentTask.Status.GENERATING
    task.save(update_fields=['status'])

    agent = task.agent
    if not agent or not agent.is_active:
        task.status = AgentTask.Status.FAILED
        task.save(update_fields=['status'])
        logger.warning("Agent not active for task %s", task_id)
        return

    start_time = time.time()

    # --- LLM call placeholder ---
    # TODO: Replace with actual LLM provider call (OpenAI, Anthropic, etc.)
    prompt = task.prompt_used or (task.prompt_template.template_text if task.prompt_template else agent.system_prompt)
    generated = f"[PLACEHOLDER] Generated content for: {task.title}"
    input_tokens = 0
    output_tokens = 0
    success = True
    error_msg = ""
    # --- End placeholder ---

    elapsed_ms = int((time.time() - start_time) * 1000)

    # Log execution
    AgentExecutionLog.objects.create(
        task=task,
        agent=agent,
        prompt_sent=prompt,
        response_received=generated,
        model_used=agent.model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        execution_time_ms=elapsed_ms,
        estimated_cost=0,
        success=success,
        error_message=error_msg,
    )

    if success:
        task.generated_content = generated
        task.prompt_used = prompt
        task.status = AgentTask.Status.IN_REVIEW
    else:
        task.status = AgentTask.Status.FAILED

    task.save(update_fields=['generated_content', 'prompt_used', 'status'])
    logger.info("Agent task %s executed — status: %s", task_id, task.status)


@shared_task
def run_campaign_batch(campaign_id):
    """Queue all pending tasks in a campaign for execution."""
    from .models import AgentTask, Campaign

    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        logger.error("Campaign %s not found", campaign_id)
        return

    queued_tasks = campaign.tasks.filter(status=AgentTask.Status.QUEUED)
    count = 0
    for task in queued_tasks:
        execute_agent_task.delay(task.pk)
        count += 1

    logger.info("Dispatched %d tasks for campaign %s", count, campaign.name)
    return count
