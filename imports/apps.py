"""
Django app configuration for imports module
"""

from django.apps import AppConfig


class ImportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "imports"
    verbose_name = "Bulk Imports"
