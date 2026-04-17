

from pathlib import Path
from dotenv import load_dotenv
import os
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecureq5nwe#wzr*n3$97z')

DEBUG = os.getenv('DEBUG', 'True') == 'True'


#ip adres schreiben
#ALLOWED_HOSTS = ['127.0.0.1']
ALLOWED_HOSTS = []



LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s %(module)s:%(lineno)d - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '%(asctime)s %(levelname)s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    'paxton_file': {
        '()': 'Tabelle.logging.MonthlyFileHandler',
        'level': 'INFO',
        'formatter': 'verbose',
        'dirname': r'K:\DIT\Applikation\Schließmanagement\Paxton_api\LOGdjango',
        'filename_prefix': 'django-paxton',
    },
    },
    'loggers': {
        'paxton': {
            'handlers': ['paxton_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },

        '': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
    }
}


# Application Definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'Tabelle.apps.TabelleConfig',
    'Formular.apps.FormularConfig',
    'Neue_Berechtigungsname.apps.NeueBerechtigungsnameConfig',
    'synchronisation.apps.SynchronisationConfig'
    # 'tests'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'coolsite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'coolsite.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": "SAP_Daten",
        "HOST": "sql20",
        "PORT": "",
        "OPTIONS": {
            "driver": "ODBC Driver 18 for SQL Server",
            "extra_params": "Encrypt=yes;TrustServerCertificate=yes;",
        },
    }
}




AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]




LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True









PAXTON_API_BASE = os.getenv('PAXTON_API_BASE', 'https://sr00044444.medi.local:8443/api/v1').rstrip("/")
PAXTON_CERT_PATH = os.getenv(
    "PAXTON_CERT_PATH",
    r"K:\DIT\Applikation\Schließmanagement\Paxton_api\Net2API.crt",
)
PAXTON_API_KEY = os.getenv('PAXTON_API_KEY', '')
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'Formular', 'static'),
    os.path.join(BASE_DIR, 'Neue_Berechtigungsname', 'static'),
    os.path.join(BASE_DIR, 'Tabelle', 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')



DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
