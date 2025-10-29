"""
WSGI config for django_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

# Створюємо WSGI application (він автоматично викликає django.setup())
application = get_wsgi_application()

# ==========================
# AUTOMATIC MIGRATIONS
# ==========================
if os.environ.get('DATABASE_URL'):
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"Migrations skipped or failed: {e}")

    # ==========================
    # CREATE SUPERUSER
    # ==========================
    User = get_user_model()
    if not User.objects.filter(username=os.environ.get('USERNAME', 'admin')).exists():
        User.objects.create_superuser(
            username=os.environ.get('USERNAME', 'admin'),
            email=os.environ.get('EMAIL', 'admin@example.com'),
            password=os.environ.get('PASSWORD', 'adminpassword')
        )
        print("Superuser created.")
