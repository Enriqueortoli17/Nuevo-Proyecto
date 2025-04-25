# proyecto_profesional/proyecto_config/asgi.py

import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# --- MODIFICADO: Cambia la ruta del módulo de settings ---
# Al igual que con WSGI, el servidor ASGI (Daphne, Uvicorn) debe configurar
# DJANGO_SETTINGS_MODULE a 'proyecto_config.settings.production' en producción.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_config.settings.development')
django.setup()

# Importa websocket_urlpatterns DESPUÉS de django.setup()
from proyecto_config.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})