"""
Custom template filters for job calculations.
"""

from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def div(value, arg):
    """Divide value by arg, handling potential division by zero."""
    try:
        if arg == 0:
            return 0
        return Decimal(str(value)) / Decimal(str(arg))
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def sub(value, arg):
    """Subtract arg from value."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (TypeError, ValueError):
        return value


@register.filter
def multiply(value, arg):
    """Multiply value by arg."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (TypeError, ValueError):
        return value


@register.filter
def percentage(value, arg):
    """Calculate what percentage value is of arg."""
    try:
        if arg == 0:
            return 0
        return (Decimal(str(value)) / Decimal(str(arg))) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return 0