import os


def env_vars(request):
    return {
        'ENV_SITE_NAME': os.getenv('SITE_NAME')
    }
