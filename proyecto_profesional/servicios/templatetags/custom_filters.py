from django import template
from django.utils.html import escape # Para escapar HTML si es necesario
import datetime

register = template.Library()

@register.filter(name='format_timedelta')
def format_timedelta(delta):
    """
    Formatea un objeto datetime.timedelta en un formato legible (ej: Xd Yh Zm).
    Maneja None y duraciones cortas.
    """
    if isinstance(delta, datetime.timedelta):
        days = delta.days
        total_seconds = int(delta.total_seconds())

        # Ignorar microsegundos o manejar deltas negativos si es necesario
        if total_seconds < 0:
            return "N/A" # O manejar negativo como prefieras

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Ajustar horas y minutos según los días
        hours %= 24 # Las horas solo van hasta 23 dentro de un día

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        # Mostrar minutos si es la única unidad > 0 o si no hay días
        if minutes > 0 and (days == 0 or not parts):
            parts.append(f"{minutes}m")
        # Si todo fue 0 (o negativo), mostrar "0m"
        if not parts:
             # Podrías añadir segundos aquí si quisieras más precisión para tiempos < 1m
             # if seconds > 0:
             #    parts.append(f"{seconds}s")
             # else:
             #    parts.append("0s") # o "0m"
             parts.append("0m")


        return " ".join(parts)
    else:
        # Si no es un timedelta (ej. None o un string), devuelve un guion
        return "-"

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
