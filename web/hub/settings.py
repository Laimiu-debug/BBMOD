import os
import sys
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR.parent))
DEBUG = os.environ.get('BBMOD_DEBUG', '0') == '1'
SECRET_KEY = os.environ.get('BBMOD_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('请配置 BBMOD_SECRET_KEY，或在本地使用 BBMOD_DEBUG=1。')
    SECRET_KEY = 'local-development-only-not-for-production-7854200123456789'
ALLOWED_HOSTS = [s.strip() for s in os.environ.get('BBMOD_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',') if s.strip()]
DATA_DIR = Path(os.environ.get('BBMOD_DATA_DIR', str(BASE_DIR / 'var'))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
                  'django.contrib.messages', 'django.contrib.staticfiles', 'catalog']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
              'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware', 'catalog.middleware.AccountMiddleware',
              'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
              'catalog.middleware.SecurityHeadersMiddleware']
ROOT_URLCONF = 'hub.urls'
WSGI_APPLICATION = 'hub.wsgi.application'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request',
                 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': DATA_DIR / 'db.sqlite3', 'OPTIONS': {'timeout': 30}}}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_ROOT = DATA_DIR / 'private'
DESKTOP_DOWNLOAD_ROOT = Path(os.environ.get('BBMOD_DESKTOP_DOWNLOAD_ROOT', str(DATA_DIR / 'desktop')))
DESKTOP_DOWNLOAD_ACCEL = os.environ.get('BBMOD_DESKTOP_DOWNLOAD_ACCEL', '0') == '1'
WIKI_ROOT = Path(os.environ.get('BBMOD_WIKI_ROOT', str(DATA_DIR / 'wiki'))).resolve()
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/workshop/'
LOGOUT_REDIRECT_URL = '/'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = 'bbmod_sessionid'
CSRF_COOKIE_NAME = 'bbmod_csrftoken'
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 12 * 60 * 60
HTTPS = os.environ.get('BBMOD_HTTPS', '0') == '1'
TRUST_PROXY = os.environ.get('BBMOD_TRUST_PROXY', '0') == '1'
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
SECURE_SSL_REDIRECT = HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if HTTPS else None
SECURE_HSTS_SECONDS = 31536000 if HTTPS else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_TRUSTED_ORIGINS = [s for s in os.environ.get('BBMOD_CSRF_ORIGINS', '').split(',') if s]
CSRF_FAILURE_VIEW = 'catalog.views.csrf_failure'
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
MAX_MOD_BYTES = int(os.environ.get('BBMOD_MAX_UPLOAD_MB', '100')) * 1024 * 1024
MAX_DESKTOP_BYTES = 300 * 1024 * 1024
AUTHOR_QUOTA_BYTES = int(os.environ.get('BBMOD_AUTHOR_QUOTA_MB', '2048')) * 1024 * 1024
UPLOADS_PER_DAY = 30
