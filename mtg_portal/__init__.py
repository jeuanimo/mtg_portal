"""
mtg_portal - Django project for Mitchell Technology Group
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
