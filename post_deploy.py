import os

import django
from django.contrib.auth import get_user_model
from django.core.management import call_command


def run():
    print("Post-deploy script started")

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
    django.setup()

    if os.environ.get('DATABASE_URL'):
        try:
            call_command('migrate', interactive=False)
        except Exception as e:
            print(f"Migrations skipped or failed: {e}")

        User = get_user_model()
        call_command('flush', interactive=False)
        if not User.objects.filter(username=os.environ.get('USERNAME', 'admin')).exists():
            User.objects.create_superuser(
                username=os.environ.get('USERNAME', 'admin'),
                email=os.environ.get('EMAIL', 'admin@example.com'),
                password=os.environ.get('PASSWORD', 'adminpassword')
            )
        print("Superuser created.")
    # call_command('collectstatic', '--noinput')
    print("Post-deploy script finished")

if __name__ == '__main__':
    run()
