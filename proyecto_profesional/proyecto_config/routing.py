from django.urls import re_path
# La referencia a 'servicios.consumers' sigue siendo válida porque
# 'servicios' es una app registrada en INSTALLED_APPS
from servicios.consumers import ServicioConsumer, OrdenesConsumer

websocket_urlpatterns = [
    re_path(r"^ws/servicios/$", ServicioConsumer.as_asgi()),
    re_path(r"^ws/ordenes/$", OrdenesConsumer.as_asgi()),
]