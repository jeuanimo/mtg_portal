from django import template

register = template.Library()


@register.filter
def div(value, arg):
    """Divide value by arg."""
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0
