"""
Local development settings.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Use SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# Debug toolbar
INSTALLED_APPS += ['debug_toolbar', 'django_extensions']  # noqa: F405
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
INTERNAL_IPS = ['127.0.0.1']

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable whitenoise compression for development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
