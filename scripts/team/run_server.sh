#!/usr/bin/env bash
# Start the SUT against the team DB.  MODE=perf uses gunicorn (same build for all k6 runs).
set -euo pipefail
cd "$(dirname "$0")/../.."
export DJANGO_SETTINGS_MODULE=tests.team.settings_test
PORT=${PORT:-8000}
if [ "${MODE:-dev}" = "perf" ]; then
  exec .venv/bin/gunicorn hpl_ims.wsgi -w 2 -b 127.0.0.1:$PORT --env DJANGO_SETTINGS_MODULE=tests.team.settings_test
else
  exec .venv/bin/python manage.py runserver 127.0.0.1:$PORT --noreload
fi
