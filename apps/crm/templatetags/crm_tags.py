from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary in templates."""
    if dictionary is None:
        return None
    return dictionary.get(key, [])


@register.filter
def status_badge_class(status):
    """Return Bootstrap badge class for lead status."""
    classes = {
        'new': 'bg-primary',
        'contacted': 'bg-info',
        'discovery': 'bg-warning text-dark',
        'proposal': 'bg-secondary',
        'negotiation': 'bg-dark',
        'won': 'bg-success',
        'lost': 'bg-danger',
    }
    return classes.get(status, 'bg-secondary')


@register.filter
def priority_badge_class(priority):
    """Return Bootstrap badge class for priority."""
    classes = {
        'low': 'bg-secondary',
        'medium': 'bg-info',
        'high': 'bg-warning text-dark',
        'urgent': 'bg-danger',
    }
    return classes.get(priority, 'bg-secondary')


@register.filter
def task_status_class(status):
    """Return Bootstrap badge class for task status."""
    classes = {
        'pending': 'bg-warning text-dark',
        'in_progress': 'bg-info',
        'completed': 'bg-success',
        'cancelled': 'bg-secondary',
    }
    return classes.get(status, 'bg-secondary')


@register.simple_tag
def lead_status_icon(status):
    """Return Bootstrap icon for lead status."""
    icons = {
        'new': 'bi-star-fill',
        'contacted': 'bi-telephone-fill',
        'discovery': 'bi-search',
        'proposal': 'bi-file-text-fill',
        'negotiation': 'bi-chat-dots-fill',
        'won': 'bi-trophy-fill',
        'lost': 'bi-x-circle-fill',
    }
    return icons.get(status, 'bi-circle-fill')
