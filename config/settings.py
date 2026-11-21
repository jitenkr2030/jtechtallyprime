"""
JTech Tally Bridge - Application Settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


# --- Tally connection ---
TALLY_HOST = os.getenv("TALLY_HOST", "auto")
TALLY_PORT = int(os.getenv("TALLY_PORT", "9000"))
TALLY_TIMEOUT = int(os.getenv("TALLY_TIMEOUT", "60"))
TALLY_PROFILE = os.getenv("TALLY_PROFILE", "auto").lower()

# --- Storage paths ---
DATABASE_PATH = BASE_DIR / os.getenv(
    "DATABASE_PATH", "data/jtech_tally_bridge.sqlite3"
)
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "data")
EXPORTS_DIR = BASE_DIR / os.getenv("EXPORTS_DIR", "data/exports")

# --- Application flags ---
DEBUG = _bool(os.getenv("DEBUG", "False"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = BASE_DIR / os.getenv("LOG_FILE", "data/jtech_tally_bridge.log")

# --- Django ---
DJANGO_SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DJANGO_DEBUG = _bool(os.getenv("DJANGO_DEBUG", "True"))
DJANGO_ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# --- Convenience ---
TALLY_URL = f"http://{TALLY_HOST}:{TALLY_PORT}/"

# Default transaction pagination: monthly chunks
DEFAULT_PAGE_DAYS = 30
