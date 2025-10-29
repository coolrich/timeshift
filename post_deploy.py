import os
from django.core.management import call_command
from django.contrib.auth import get_user_model
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

if os.environ.get('DATABASE_URL'):
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"Migrations skipped or failed: {e}")

    User = get_user_model()
    if not User.objects.filter(username=os.environ.get('USERNAME', 'admin')).exists():
        User.objects.create_superuser(
            username=os.environ.get('USERNAME', 'admin'),
            email=os.environ.get('EMAIL', 'admin@example.com'),
            password=os.environ.get('PASSWORD', 'adminpassword')
        )
        print("Superuser created.")
