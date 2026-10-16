"""Django settings for the Crop Disease Detector backend (M4.2: SQLite dev DB)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    """Minimal .env loader (no extra dependency). Real env vars win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


def env_str(name, default=""):
    """Like os.environ.get, but an empty value (e.g. `EMAIL_HOST=` in .env) falls back to the default."""
    return os.environ.get(name, "").strip() or default


def env_int(name, default):
    return int(env_str(name, str(default)))


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-change-me"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.predictions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# SQLite for local development (M4.x). MySQL arrives in M5.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Dar_es_Salaam"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Sessions & CSRF -------------------------------------------------------
# The frontend reads the `csrftoken` cookie in JS (auth.js getCsrfToken) and
# sends it back as X-CSRFToken, so CSRF_COOKIE_HTTPONLY must stay False.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# Origins allowed to make unsafe requests (needed when the Vite dev server
# proxies /api to Django: the browser Origin is the Vite origin).
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173"
)
# Default session lifetime when "remember me" is checked (2 weeks).
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# --- Google Sign-In (M4.2) ----------------------------------------------------
# Public OAuth *Client ID* only. It is used to verify the audience of Google ID
# tokens server-side and is also served to the frontend via
# GET /api/auth/google/config/. There is no client secret in this flow.
GOOGLE_CLIENT_ID = env_str("GOOGLE_CLIENT_ID")

# --- Password reset & email (M4.2) --------------------------------------------
# Public origin of the frontend; used to build the link inside reset emails.
FRONTEND_ORIGIN = env_str("FRONTEND_ORIGIN", "http://localhost:8080").rstrip("/")
# Reset tokens are stateless HMAC tokens (Django's PasswordResetTokenGenerator):
# nothing is stored in the database, and a token dies as soon as the password changes.
PASSWORD_RESET_TIMEOUT = env_int("PASSWORD_RESET_TIMEOUT", 60 * 60)  # seconds (default 1 hour)
# Development default prints emails (decoded, copy-pasteable) to the runserver terminal; nothing is delivered.
# Production: set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend and the EMAIL_* vars.
EMAIL_BACKEND = env_str(
    "EMAIL_BACKEND",
    "apps.accounts.email_backends.ReadableConsoleEmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env_str("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 25)
EMAIL_HOST_USER = env_str("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env_str("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = env_str("DEFAULT_FROM_EMAIL", "Crop Disease Detector <no-reply@localhost>")

# --- Prediction upload limits (M4.2) -----------------------------------------
# Keep in sync with MAX_FILE_SIZE in public/site/js/scan.js (5 MB).
PREDICT_MAX_UPLOAD_BYTES = env_int("PREDICT_MAX_UPLOAD_BYTES", 5 * 1024 * 1024)
PREDICT_MAX_IMAGE_PIXELS = env_int("PREDICT_MAX_IMAGE_PIXELS", 40_000_000)
# Dotted path of the inference engine (see apps/predictions/inference.py).
PREDICTION_ENGINE = env_str("PREDICTION_ENGINE", "apps.predictions.inference.NullInferenceEngine")
# Uploads are validated in memory and never written to disk: keep them in memory
# (requests larger than the cap are rejected before parsing, see predictions/views.py).
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.MemoryFileUploadHandler"]
FILE_UPLOAD_MAX_MEMORY_SIZE = PREDICT_MAX_UPLOAD_BYTES + 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.accounts.authentication.CsrfEnforcedSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "apps.accounts.exceptions.json_exception_handler",
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
    # Applied only to views that declare throttle_scope (password flows).
    "DEFAULT_THROTTLE_RATES": {
        "password-reset": "10/hour",
        "password-reset-confirm": "20/hour",
        "change-password": "10/hour",
    },
}
