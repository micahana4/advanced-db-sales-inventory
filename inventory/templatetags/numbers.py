from decimal import Decimal

from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def numeric_intcomma(value):
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return intcomma(value)
    return value
