#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ is required"'
if [ ! -d .venv ]; then
    "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/configure.py
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python scripts/create_admin.py
exec ./start.sh
