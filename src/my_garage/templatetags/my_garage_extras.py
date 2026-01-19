from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value, arg):
    """
    Replaces all occurrences of arg[0] with arg[1] in the given string.
    Usage: {{ "some_string"|replace:"_," }}
    """
    if isinstance(arg, str) and ',' in arg:
        old, new = arg.split(',', 1)
        return value.replace(old, new)
    return value
