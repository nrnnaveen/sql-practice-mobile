import os
import logging

SECRET_KEY = os.environ.get("SECRET_KEY") or "dev_secret_key_change_in_production"

if not os.environ.get("SECRET_KEY"):
    logging.warning(
        "SECRET_KEY environment variable is not set. "
        "Using an insecure default – set SECRET_KEY in production!"
    )

# ── Fernet encryption key ─────────────────────────────────────────────────────
# Used to encrypt per-user database passwords stored in SQLite.
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# If absent, a hard-coded fallback is used (insecure – always set in production).
CIPHER_KEY = os.environ.get("CIPHER_KEY", "")

# ── Google OAuth 2.0 ─────────────────────────────────────────────────────────
# Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET as environment variables.
# For localhost dev, add http://127.0.0.1:5000/login/google/callback as an
# authorised redirect URI in the Google Cloud Console.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    logging.warning(
        "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is not set. "
        "Google Sign-In will be disabled."
    )

# Explicit redirect URI override (optional).  When set, this value is used
# instead of the dynamically generated url_for() result.  Useful when the
# app sits behind a reverse proxy that changes the visible scheme/host.
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")

# OAuth scopes requested from Google.
GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Authorized redirect URIs – register all of these in the Google Cloud Console.
AUTHORIZED_REDIRECT_URIS = [
    uri
    for uri in [
        GOOGLE_OAUTH_REDIRECT_URI,
        os.environ.get("APP_URL", ""),
        "http://localhost:5000/login/google/callback",
        "http://127.0.0.1:5000/login/google/callback",
    ]
    if uri
]

# Authorized JavaScript origins – register these in the Google Cloud Console.
AUTHORIZED_JAVASCRIPT_ORIGINS = [
    origin
    for origin in [
        os.environ.get("APP_URL", ""),
        "http://localhost:5000",
        "http://localhost:8100",
    ]
    if origin
]

# Trusted origins for CORS / origin validation.
TRUSTED_ORIGINS = list(
    {
        origin
        for origin in [
            os.environ.get("APP_URL", ""),
            "http://localhost:5000",
            "http://localhost:8100",
        ]
        if origin
    }
)

# ── MySQL ────────────────────────────────────────────────────────────────────
# On Railway, set MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE as
# environment variables. When those are absent the app falls back to localhost so
# it still starts, but queries will return a connection-error message rather than
# crashing the server.
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "test_db"),
    "connection_timeout": 10,
}

# ── MySQL Admin (for per-user database creation) ──────────────────────────────
# Uses a privileged account that can CREATE USER / CREATE DATABASE.
# Defaults to the same credentials as MYSQL_CONFIG when not separately set.
MYSQL_ADMIN_CONFIG = {
    "host": os.environ.get("MYSQL_ADMIN_HOST", os.environ.get("MYSQL_HOST", "localhost")),
    "port": int(os.environ.get("MYSQL_ADMIN_PORT", os.environ.get("MYSQL_PORT", 3306))),
    "user": os.environ.get("MYSQL_ADMIN_USER", os.environ.get("MYSQL_USER", "root")),
    "password": os.environ.get("MYSQL_ADMIN_PASSWORD", os.environ.get("MYSQL_PASSWORD", "")),
    "connection_timeout": 10,
}

# ── PostgreSQL ───────────────────────────────────────────────────────────────
# On Railway, DATABASE_URL (postgres://…) is the standard way to pass the full
# connection string. We parse it when present; individual env-vars act as the
# fallback so local development keeps working.
_pg_url = os.environ.get("DATABASE_URL", "")

if _pg_url.startswith("postgres"):
    # Parse the Railway-style URL into keyword arguments for psycopg2.connect()
    import re
    _m = re.match(
        r"postgres(?:ql)?://(?P<user>[^:]+):(?P<password>[^@]+)@"
        r"(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<database>.+)",
        _pg_url,
    )
    if _m:
        POSTGRES_CONFIG = {
            "host": _m.group("host"),
            "port": int(_m.group("port") or 5432),
            "user": _m.group("user"),
            "password": _m.group("password"),
            "database": _m.group("database"),
            "connect_timeout": 10,
        }
    else:
        POSTGRES_CONFIG = {"dsn": _pg_url, "connect_timeout": 10}
else:
    POSTGRES_CONFIG = {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", 5432)),
        "user": os.environ.get("POSTGRES_USER", "postgres"),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
        "database": os.environ.get("POSTGRES_DATABASE", "test_db"),
        "connect_timeout": 10,
    }

# ── PostgreSQL Admin (for per-user database creation) ─────────────────────────
# Uses a superuser account that can CREATE ROLE / CREATE DATABASE.
_pg_admin_url = os.environ.get("POSTGRES_ADMIN_URL", "")
if _pg_admin_url.startswith("postgres"):
    import re as _re
    _ma = _re.match(
        r"postgres(?:ql)?://(?P<user>[^:]+):(?P<password>[^@]+)@"
        r"(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<database>.+)",
        _pg_admin_url,
    )
    if _ma:
        POSTGRES_ADMIN_CONFIG = {
            "host": _ma.group("host"),
            "port": int(_ma.group("port") or 5432),
            "user": _ma.group("user"),
            "password": _ma.group("password"),
            "database": _ma.group("database"),
            "connect_timeout": 10,
        }
    else:
        POSTGRES_ADMIN_CONFIG = {"dsn": _pg_admin_url, "connect_timeout": 10}
else:
    POSTGRES_ADMIN_CONFIG = {
        "host": os.environ.get("POSTGRES_ADMIN_HOST", os.environ.get("POSTGRES_HOST", "localhost")),
        "port": int(os.environ.get("POSTGRES_ADMIN_PORT", os.environ.get("POSTGRES_PORT", 5432))),
        "user": os.environ.get("POSTGRES_ADMIN_USER", os.environ.get("POSTGRES_USER", "postgres")),
        "password": os.environ.get("POSTGRES_ADMIN_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "")),
        "database": os.environ.get("POSTGRES_ADMIN_DATABASE", "postgres"),
        "connect_timeout": 10,
    }

