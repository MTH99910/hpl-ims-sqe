#!/usr/bin/env python
"""Cross-platform reset (Linux, macOS, Windows): delete the team DB, migrate, seed, refresh golden.sqlite3.
Equivalent to scripts/team/reset_db.sh.   Usage:  python scripts/team/reset_db.py"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.team.settings_test")
db = Path(os.environ.get("TEAM_DB", ROOT / "tests/team/data/team.sqlite3"))
db.unlink(missing_ok=True)
subprocess.run([sys.executable, str(ROOT / "manage.py"), "migrate", "-v0"], cwd=ROOT, check=True)
subprocess.run([sys.executable, str(ROOT / "scripts/team/seed_team.py")], cwd=ROOT, check=True)
shutil.copyfile(db, ROOT / "tests/team/data/golden.sqlite3")
print(f"Reset complete: {db} (golden snapshot refreshed)")
