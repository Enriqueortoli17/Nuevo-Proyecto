# proyecto_profesional/proyecto_config/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

# --- MODIFICADO: Cambia la ruta del módulo de settings ---
# Asegúrate que el servidor WSGI (Gunicorn, etc.) configure la variable de entorno
# DJANGO_SETTINGS_MODULE a 'proyecto_config.settings.production' en producción.
# El setdefault aquí es más un fallback para desarrollo si no se define externamente.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proyecto_config.settings.development")

application = get_wsgi_application()
