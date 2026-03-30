"""organs/apps.py"""
from django.apps import AppConfig

class OrgansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'organs'
    verbose_name = 'Organs & Matching'
