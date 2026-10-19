#!/usr/bin/env sh
set -eu
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python scripts/create_admin.py
exec python scripts/serve.py
