#!/bin/sh
set -e

mkdir -p /app/static

python manage.py migrate
python manage.py collectstatic --noinput

exec gunicorn daystat.wsgi --bind 0.0.0.0:8000 --access-logfile - --error-logfile -
