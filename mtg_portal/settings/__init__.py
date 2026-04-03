"""
Settings module initialization.
Import from local by default; override with DJANGO_SETTINGS_MODULE env var.
"""

import os

environment = os.getenv('DJANGO_ENV', 'local')

if environment == 'production':
    from .production import *  # noqa: F401,F403
else:
    from .local import *  # noqa: F401,F403
