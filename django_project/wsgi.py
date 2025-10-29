"""
WSGI config for django_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command
from django_project.post_deploy import run

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

application = get_wsgi_application()

call_command('collectstatic', '--noinput')
run()
