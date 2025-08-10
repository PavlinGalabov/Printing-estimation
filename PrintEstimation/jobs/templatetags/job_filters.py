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


@register.filter
def hours_minutes(value):
    """Convert minutes to hours and minutes format (e.g., 90 -> '1h 30m')."""
    try:
        minutes = int(float(value))
        if minutes == 0:
            return "0m"
        elif minutes < 60:
            return f"{minutes}m"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h {remaining_minutes}m"
    except (TypeError, ValueError):
        return "0m"