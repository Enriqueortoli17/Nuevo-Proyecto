import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# --- LÍNEA MODIFICADA ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_config.settings')
django.setup()

# --- LÍNEA MODIFICADA ---
# Importa websocket_urlpatterns DESPUÉS de django.setup()
# Asumiendo que routing.py está ahora en proyecto_config
from proyecto_config.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})