# proyecto_profesional/proyecto_config/settings/base.py

from pathlib import Path
import environ
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# --- MODIFICADO: Ajustar BASE_DIR ---
# Antes: Path(__file__).resolve().parent.parent
# Ahora apunta a la carpeta raíz 'proyecto_profesional/' desde 'settings/base.py'
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- NUEVO: Inicializar django-environ ---
# (Esta parte ya la tenías, está bien)
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)
# Lee el archivo .env que estará en BASE_DIR (proyecto_profesional/.env)
# Asegúrate de que el archivo .env esté en la raíz del proyecto 'proyecto_profesional/'
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))
# --- FIN NUEVO ---

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# (Esta parte ya la tenías, está bien para la base)
SECRET_KEY = env('SECRET_KEY', default='django-insecure-valor-secreto-temporal')

# SECURITY WARNING: don't run with debug turned on in production!
# (Leer DEBUG desde .env está bien aquí, pero lo sobrescribiremos)
DEBUG = env('DEBUG')

# ALLOWED_HOSTS lo definiremos en development.py y production.py
ALLOWED_HOSTS = [] # Dejar vacío en base.py

# Application definition
# (Sin cambios aquí, tus INSTALLED_APPS, MIDDLEWARE están bien)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'servicios',
    'widget_tweaks',
    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- MODIFICADO: Ajustar ruta a urls, wsgi, asgi ---
ROOT_URLCONF = 'proyecto_config.urls' # Sigue igual

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Correcto
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages', # <-- ESTA LÍNEA FALTABA
            ],
            'builtins': [
                'servicios.templatetags.custom_filters', # Correcto
            ]
        },
    },
]

WSGI_APPLICATION = 'proyecto_config.wsgi.application' # Sigue igual
ASGI_APPLICATION = 'proyecto_config.asgi.application' # Sigue igual


# Database
# (Tu configuración con environ está bien para la base)
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db_profesional.sqlite3"}')
}


# Password validation
# (Sin cambios)
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# Internationalization
# (Sin cambios)
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# (Sin cambios)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Default primary key field type
# (Sin cambios)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Channels
# (Dejaremos InMemory aquí, pero production.py usará Redis si lo configuras)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Twilio (Leer desde .env está bien aquí)
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default=None)
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default=None)
TWILIO_WHATSAPP_FROM = env('TWILIO_WHATSAPP_FROM', default=None)

# --- FIN base.py ---