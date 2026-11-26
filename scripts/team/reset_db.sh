#!/usr/bin/env bash
# Reset the isolated team DB to the known seeded state (used between every run).
set -euo pipefail
cd "$(dirname "$0")/../.."
export DJANGO_SETTINGS_MODULE=tests.team.settings_test
PY=${PY:-.venv/bin/python}
DB=${TEAM_DB:-tests/team/data/team.sqlite3}
rm -f "$DB"
$PY manage.py migrate -v0
$PY scripts/team/seed_team.py
cp "$DB" tests/team/data/golden.sqlite3   # same steps as reset_db.py (cross-platform)
echo "Reset complete: $DB (golden snapshot refreshed)"
