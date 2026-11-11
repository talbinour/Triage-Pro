"""
Django settings — tout dans MongoDB via pymongo + JWT
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-r!n-ne%4m^%suhgu5=^3s8-f=2#cz#o$&w1bp=)#aucejr*w)1'
JWT_SECRET = 'jwt-triage-secret-key-changez-en-production-2026'

DEBUG = True

# ⚠️ Mettez votre vraie IP WiFi ici (pas l'IP VirtualBox 192.168.56.x)
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'triage',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'triage_backend.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
    ]},
}]

WSGI_APPLICATION = 'triage_backend.wsgi.application'

DATABASES = {}

# ─── MongoDB Atlas ────────────────────────────────────────────────────────────
import pymongo
MONGO_URI = 'mongodb+srv://talbinourelhouda00_db_user:Zmq4qcjz6875yUpN@cluster0.lvldhyo.mongodb.net/?appName=Cluster0'
MONGO_CLIENT = pymongo.MongoClient(MONGO_URI)
MONGO_DB = MONGO_CLIENT['triage_db']

# ─── DRF ─────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# ─── Email Gmail ──────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'talbinourelhouda00@gmail.com'
EMAIL_HOST_PASSWORD = 'ljrb yznr mdnl xoya'

# ─── URLs ─────────────────────────────────────────────────────────────────────
# Remplacez 192.168.1.X par votre vraie IP WiFi (résultat de ipconfig)
FRONTEND_URL = 'http://192.168.1.13:8100'

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8100',
    'http://localhost:4200',
    'http://192.168.1.13:8100',   # ← même IP WiFi
]
CORS_ALLOW_CREDENTIALS = True

# ─── I18N ─────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'