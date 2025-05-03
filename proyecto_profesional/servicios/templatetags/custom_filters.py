from django import template

register = template.Library()


@register.filter
def get_item(form, key):
    """
    Devuelve el campo del formulario usando la clave.
    Equivale a: form[key]
    """
    try:
        return form.__getitem__(key)
    except Exception:
        return None


@register.filter
def lookup(dictionary, key):
    """
    Devuelve el valor para 'key' en el diccionario.
    """
    try:
        return dictionary.get(key)
    except Exception:
        return None


@register.filter
def trim(value):
    """
    Elimina espacios en blanco al inicio y al final de una cadena.
    """
    try:
        return value.strip()
    except Exception:
        return value
