"""
WSGI config for proyecto_profesional project. # <-- Actualiza nombre del proyecto si quieres

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# --- LÍNEA MODIFICADA ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_config.settings')

application = get_wsgi_application()