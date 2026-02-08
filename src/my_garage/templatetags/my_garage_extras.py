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


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    Usage: {{ my_dict|get_item:key_var }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
