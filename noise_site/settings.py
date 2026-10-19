import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [value.strip() for value in os.getenv(name, default).split(',') if value.strip()]


SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set SECRET_KEY in .env or run ./install.sh first.')
DEBUG = env_bool('DEBUG')
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'noise', 'site_accounts',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'noise_site.middleware.UploadSizeLimitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
if env_bool('TRACK_VISITS'):
    MIDDLEWARE.append('noise.middleware.NoiseVisitTrackingMiddleware')
ROOT_URLCONF = 'noise_site.urls'
WSGI_APPLICATION = 'noise_site.wsgi.application'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'noise_site.context_processors.site',
    ]},
}]
DATA_DIR = Path(os.getenv('DATA_DIR', str(BASE_DIR / 'data')))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3', 'NAME': DATA_DIR / 'db.sqlite3',
    'OPTIONS': {'timeout': 20},
}}
if os.getenv('DB_HOST'):
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.environ['DB_HOST'], 'PORT': os.getenv('DB_PORT', '5432'),
        'NAME': os.environ['DB_NAME'], 'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'sslmode': os.getenv('DB_SSLMODE', 'prefer')},
    }}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'assets']
MEDIA_ROOT = DATA_DIR / 'media'
MEDIA_URL = '/media/'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
if os.getenv('AWS_STORAGE_BUCKET_NAME'):
    STORAGES['default'] = {'BACKEND': 'storages.backends.s3.S3Storage'}
    AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL') or None
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_FILE_OVERWRITE = False
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/noise/'
LOGOUT_REDIRECT_URL = '/noise/'
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT')
SESSION_COOKIE_SECURE = env_bool('COOKIE_SECURE')
CSRF_COOKIE_SECURE = env_bool('COOKIE_SECURE')
if env_bool('TRUST_PROXY_HTTPS'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SITE_TITLE = os.getenv('SITE_TITLE', 'Noise')
SITE_TAGLINE = os.getenv('SITE_TAGLINE', 'There are no rules here')
HOME_GPS = ''
GOOGLE_MAPS_KEY = os.getenv('GOOGLE_MAPS_KEY', '')
NOISE_MEDIA_FOLDER = 'noise'
NOISE_MAX_UPLOAD_BYTES = int(os.getenv('NOISE_MAX_UPLOAD_BYTES', str(95 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = NOISE_MAX_UPLOAD_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
NOISE_AUTH_COGNITO_DOMAIN = os.getenv('NOISE_AUTH_COGNITO_DOMAIN', '')
NOISE_AUTH_COGNITO_CLIENT_ID = os.getenv('NOISE_AUTH_COGNITO_CLIENT_ID', '')
NOISE_AUTH_COGNITO_USER_POOL_ID = os.getenv('NOISE_AUTH_COGNITO_USER_POOL_ID', '')
NOISE_AUTH_COGNITO_REGION = os.getenv('NOISE_AUTH_COGNITO_REGION', 'us-east-1')
PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:8000').rstrip('/')
NOISE_AUTH_REDIRECT_URI = PUBLIC_URL + '/noise/auth/callback/'
NOISE_AUTH_LOGOUT_URI = PUBLIC_URL + '/noise/'
NOISE_AUTH_PROVIDER_MAP = {
    'google': os.getenv('NOISE_AUTH_GOOGLE_PROVIDER', ''),
    'facebook': os.getenv('NOISE_AUTH_FACEBOOK_PROVIDER', ''),
    'instagram': os.getenv('NOISE_AUTH_INSTAGRAM_PROVIDER', ''),
    'phone': '',
}
NOISE_AUTH_PHONE_ENABLED = env_bool('NOISE_AUTH_PHONE_ENABLED')
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
}
