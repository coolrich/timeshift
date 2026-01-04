# myapp/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.filter
def dotdecimal(value):
    """Примусово замінює кому на крапку і формат до float"""
    try:
        return str(float(str(value).replace(',', '.')))
    except (ValueError, TypeError):
        return value
