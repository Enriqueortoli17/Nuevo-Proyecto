# proyecto_profesional/proyecto_config/settings/production.py

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from .base import *  # Importa toda la configuración base
from .base import env  # Importa la instancia 'env' para leer variables

# --- Configuración específica para PRODUCCIÓN ---

# DEBUG siempre False en producción
DEBUG = False

# SECRET_KEY DEBE leerse desde el entorno en producción
SECRET_KEY = env(
    "SECRET_KEY"
)  # Asegúrate que esté en .env o en las variables de entorno del servidor

# Hosts permitidos en producción (DEBEN ser específicos)
# Lee desde la variable de entorno ALLOWED_HOSTS="dominio.com,www.dominio.com"
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # Leer como lista desde .env

# Configuración de Base de Datos para Producción
# Lee desde la variable de entorno DATABASE_URL="postgres://user:pass@host:port/dbname"
DATABASES = {"default": env.db("DATABASE_URL")}  # Falla si no está definida

# Configuración de Email (debes configurar un servicio real: SendGrid, Mailgun, etc.)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = env('EMAIL_HOST')
# EMAIL_PORT = env.int('EMAIL_PORT', 587)
# EMAIL_HOST_USER = env('EMAIL_HOST_USER')
# EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
# EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', True)
# DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# Configuración de Channels para producción (ejemplo con Redis)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             "hosts": [env('REDIS_URL', default='redis://localhost:6379/1')],
#         },
#     },
# }

# Configuración de Seguridad Adicional para Producción
# SECURE_SSL_REDIRECT = env.bool('DJANGO_SECURE_SSL_REDIRECT', default=True) # Redirige HTTP a HTTPS
# SESSION_COOKIE_SECURE = env.bool('DJANGO_SESSION_COOKIE_SECURE', default=True) # Cookies de sesión solo por HTTPS
# CSRF_COOKIE_SECURE = env.bool('DJANGO_CSRF_COOKIE_SECURE', default=True)     # Cookie CSRF solo por HTTPS
# SECURE_HSTS_SECONDS = env.int('DJANGO_SECURE_HSTS_SECONDS', default=31536000) # 1 año (Strict Transport Security)
# SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
# SECURE_HSTS_PRELOAD = env.bool('DJANGO_SECURE_HSTS_PRELOAD', default=True)
# SECURE_BROWSER_XSS_FILTER = env.bool('DJANGO_SECURE_BROWSER_XSS_FILTER', default=True)
# SECURE_CONTENT_TYPE_NOSNIFF = env.bool('DJANGO_SECURE_CONTENT_TYPE_NOSNIFF', default=True)
# X_FRAME_OPTIONS = env('DJANGO_X_FRAME_OPTIONS', default='DENY')


# Configuración de Sentry (si lo usas para reporte de errores)
# SENTRY_DSN = env('SENTRY_DSN', default=None)
# if SENTRY_DSN:
#     sentry_sdk.init(
#         dsn=SENTRY_DSN,
#         integrations=[DjangoIntegration()],
#         # Ajusta la tasa de muestreo para rendimiento en producción
#         traces_sample_rate=0.1,
#         # Si encuentras PII (Información Personal Identificable) en los eventos,
#         # puedes necesitar configurar before_send
#         send_default_pii=True
#     )

# WhiteNoise (ya configurado en base.py, generalmente no necesita cambios aquí)
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

print("*****************************************")
print("**** Cargando configuración PRODUCTION ****")
print("*****************************************")
