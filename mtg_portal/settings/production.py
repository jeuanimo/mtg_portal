"""
Production settings for Mitchell Technology Group Portal.
"""

import os

import dj_database_url

from .base import *  # noqa: F401,F403

DEBUG = False

# =====================================================
# CRITICAL: Fail fast if SECRET_KEY is not properly set
# =====================================================
if SECRET_KEY == 'django-insecure-change-me-in-production' or not SECRET_KEY:  # noqa: F405
    raise ValueError(
        "CRITICAL: SECRET_KEY must be set in production. "
        "Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    )

# =====================================================
# DATABASE_URL support (takes precedence over individual env vars)
# =====================================================
if os.getenv('DATABASE_URL'):
    DATABASES = {  # noqa: F405
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Disable logout via GET in production for CSRF safety (requires POST logout)
# Set ACCOUNT_LOGOUT_ON_GET=True in env to re-enable if needed
ACCOUNT_LOGOUT_ON_GET = os.getenv('ACCOUNT_LOGOUT_ON_GET', 'False').lower() in ('true', '1', 'yes')

# Ensure ALLOWED_HOSTS is set in production — filter empties so unset var gives [] not ['']
ALLOWED_HOSTS = [h for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h]

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if os.getenv('CSRF_TRUSTED_ORIGINS') else []

# Production email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Production logging — console only (Render captures stdout/stderr)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'mtg_portal': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Admin email for error notifications
ADMINS = [
    ('Admin', os.getenv('ADMIN_EMAIL', 'admin@mitchelltechgroup.com')),
]
MANAGERS = ADMINS

# Cache configuration - use Redis if available, otherwise local memory
if os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Cloudinary for media file storage (optional - only if configured)
if os.getenv('CLOUDINARY_CLOUD_NAME'):
    import cloudinary
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True,
    )
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Static files served by WhiteNoise (Cloudinary is media-only)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Additional security for production
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Performance optimization
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
