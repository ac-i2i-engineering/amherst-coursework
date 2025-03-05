from django import template

register = template.Library()


@register.filter
def trim(value):
    return value.strip()


@register.filter
def split(value, arg):
    """Split a string by the given argument"""
    return value.split(arg)


@register.filter
def safe_split(value, arg):
    if not value:
        return [""]
    parts = value.split(arg)
    return parts if len(parts) > 1 else [parts[0], ""]
