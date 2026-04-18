"""
Custom form widgets for the MTG Portal.
"""
import uuid

from django import forms


class DatalistTextInput(forms.TextInput):
    """
    A text input with an associated <datalist> for combo-box behavior.
    Users can pick from predefined suggestions OR type a custom value.
    """

    def __init__(self, choices=None, attrs=None):
        super().__init__(attrs=attrs)
        self.choices = choices or []

    def render(self, name, value, attrs=None, renderer=None):
        list_id = f"datalist_{name}_{uuid.uuid4().hex[:8]}"
        if attrs is None:
            attrs = {}
        attrs['list'] = list_id
        attrs.setdefault('class', 'form-control')
        html = super().render(name, value, attrs=attrs, renderer=renderer)
        options = ''.join(
            f'<option value="{val}">{label}</option>'
            for val, label in self.choices
        )
        html += f'<datalist id="{list_id}">{options}</datalist>'
        return forms.utils.mark_safe(html)
