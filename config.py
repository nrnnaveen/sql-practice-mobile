import os
import logging

SECRET_KEY = os.environ.get("SECRET_KEY") or "dev_secret_key_change_in_production"

if not os.environ.get("SECRET_KEY"):
    logging.warning(
        "SECRET_KEY environment variable is not set. "
        "Using an insecure default – set SECRET_KEY in production!"
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
