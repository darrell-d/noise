import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noise_site.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command

if not get_user_model().objects.filter(is_superuser=True).exists():
    if os.getenv('DJANGO_SUPERUSER_USERNAME') and os.getenv('DJANGO_SUPERUSER_PASSWORD'):
        call_command('createsuperuser', interactive=False)
    elif sys.stdin.isatty():
        print('Create your Noise administrator account:')
        call_command('createsuperuser')
    else:
        raise SystemExit('Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD for unattended installation.')
