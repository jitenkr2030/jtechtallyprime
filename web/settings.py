"""
Django settings for JTech Tally Bridge web project.

Production hardening notes:
- DEBUG is forced to False unless DJANGO_DEBUG=True explicitly.
- SECRET_KEY must be supplied via env in production; the default
  is intentionally an obvious dev-only string.
- SECURE_HSTS_SECONDS / SESSION_COOKIE_SECURE / CSRF_COOKIE_SECURE
  activate when DEBUG=False so cookies and HTTPS are enforced.
- Trusted origins for CSRF can be configured via DJANGO_ALLOWED_HOSTS.
"""

from pathlib import Path
import os
import sys

# Ensure project root is on sys.path so `config`, `core`, `modules` etc.
# are importable from inside Django.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import (  # noqa: E402
    DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS,
    DATABASE_PATH,
)


def _env_bool(name, default=False):
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


# Force DEBUG=False unless explicitly opted in
DEBUG = _env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = DJANGO_SECRET_KEY
if not DEBUG and SECRET_KEY.startswith(("dev-only", "change-me")):
    raise RuntimeError(
        "Refusing to start in production with an insecure SECRET_KEY. "
        "Set DJANGO_SECRET_KEY env var to a strong random value."
    )

ALLOWED_HOSTS = DJANGO_ALLOWED_HOSTS
if not DEBUG:
    # In production, also accept the trusted-origin pattern for CSRF
    CSRF_TRUSTED_ORIGINS = [
        f"https://{h}" for h in DJANGO_ALLOWED_HOSTS
    ]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "web.dashboard",
    "web.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DATABASE_PATH),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = False

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "data" / "static"

# WhiteNoise for production static serving
STORAGES = {
    "default": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# Production security settings
if not DEBUG:
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True

# Logging - structured for production
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "web": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# Multi-Tally connection support
# Connection profiles are read from the `app_settings` table
# (keys prefixed with `tally_profile_`).
