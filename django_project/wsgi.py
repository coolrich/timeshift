"""
WSGI config for django_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

import django
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

application = get_wsgi_application()

django.setup()

try:
    call_command('migrate', interactive=False)
except Exception as e:
    print(f"Migrations skipped or failed: {e}")