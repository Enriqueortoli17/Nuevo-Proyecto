# proyecto_profesional/proyecto_config/settings/development.py

from .base import * # Importa toda la configuración base
from .base import env # Importa la instancia 'env' de base.py para usarla aquí

# --- Configuración específica para DESARROLLO ---

# DEBUG siempre True en desarrollo
DEBUG = True

# Clave secreta (puedes usar la de .env o una simple para desarrollo)
# SECRET_KEY = env('SECRET_KEY', default='clave-secreta-solo-para-desarrollo')
# O simplemente hereda la de base.py si ya la lee de .env
# SECRET_KEY = env('SECRET_KEY') # Ya está en base.py

# Hosts permitidos en desarrollo (puedes ser más permisivo aquí)
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.1.104'] # Tus hosts locales

# Configuración de Base de Datos para Desarrollo (opcional, si quieres una diferente)
# Por defecto usará la definida en base.py (SQLite)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db_dev.sqlite3', # Un archivo diferente para dev
#     }
# }

# Configuración de Email (para que los emails se impriman en consola en lugar de enviarse)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Configuración de Channels (usa InMemory para desarrollo)
# CHANNEL_LAYERS = { # Ya está definido en base.py
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer',
#     },
# }

# Puedes añadir otras configuraciones útiles para desarrollo aquí,
# como herramientas de depuración (django-debug-toolbar si la usas)
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']

print("****************************************")
print("*** Cargando configuración DEVELOPMENT ***")
print("****************************************")