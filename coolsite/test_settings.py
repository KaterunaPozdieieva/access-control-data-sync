# test_settings.py
# Lädt alle normalen Einstellungen und überschreibt nur die DATABASES-Einstellung
from .settings import *  # importiert alle Einstellungen aus coolsite.settings

# Für Tests: benutze eine In-Memory SQLite Datenbank
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}