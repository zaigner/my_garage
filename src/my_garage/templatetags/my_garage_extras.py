from decimal import Decimal

from django import template

register = template.Library()


@register.filter(name="replace")
def replace(value, arg):
    """
    Replaces all occurrences of arg[0] with arg[1] in the given string.
    Usage: {{ "some_string"|replace:"_," }}
    """
    if isinstance(arg, str) and "," in arg:
        old, new = arg.split(",", 1)
        return value.replace(old, new)
    return value


@register.filter(name="get_item")
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    Usage: {{ my_dict|get_item:key_var }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter(name="currency_display")
def currency_display(value):
    """
    Format a Decimal as a currency string: "$X,XXX" (rounded to nearest dollar).
    Returns "—" for null/zero.
    Usage: {{ item.total_cost_basis|currency_display }}
    """
    if value is None:
        return "—"
    try:
        amount = Decimal(str(value))
    except Exception:
        return "—"
    if amount == 0:
        return "—"
    rounded = abs(amount.quantize(Decimal("1")))
    return f"${rounded:,}"


@register.filter(name="nfp_display")
def nfp_display(value):
    """
    Format a DecimalField NFP value for display.

    Positive → "+$X,XXX"  (rounded to nearest dollar)
    Negative → "−$X,XXX"  (uses minus sign U+2212, not hyphen)
    None/Zero → "—"
    """
    if value is None:
        return "—"
    try:
        amount = Decimal(str(value))
    except Exception:
        return "—"
    if amount == 0:
        return "—"
    rounded = abs(amount.quantize(Decimal("1")))
    formatted = f"{rounded:,}"
    if amount > 0:
        return f"+${formatted}"
    return f"−${formatted}"


@register.filter(name="nfp_color_class")
def nfp_color_class(value):
    """
    Return a Tailwind text-color class for an NFP value.

    Positive → "text-green-400"
    Negative → "text-red-400"
    None/Zero → "text-gray-400"
    """
    if value is None:
        return "text-gray-400"
    try:
        amount = Decimal(str(value))
    except Exception:
        return "text-gray-400"
    if amount > 0:
        return "text-green-400"
    if amount < 0:
        return "text-red-400"
    return "text-gray-400"
