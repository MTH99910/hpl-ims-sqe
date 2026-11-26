"""Team test settings: same app as upstream, but an isolated SQLite file so the
committed db.sqlite3 is never touched. Selected via DJANGO_SETTINGS_MODULE."""
import os
from hpl_ims.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("TEAM_DB", str(BASE_DIR / "tests" / "team" / "data" / "team.sqlite3")),  # noqa: F405
    }
}
# Faster password hashing for tests only (does not change app behaviour under test).
if os.environ.get("FAST_HASH"):
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
