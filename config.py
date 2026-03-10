import os
import secrets

# -----------------------------
# Flask secret key
# -----------------------------
# Use environment variable if provided, else generate a random key
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(16)

# -----------------------------
# MySQL config (PlanetScale / cloud)
# -----------------------------
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "your_mysql_host_here"),
    "user": os.environ.get("MYSQL_USER", "your_mysql_user_here"),
    "password": os.environ.get("MYSQL_PASSWORD", "your_mysql_password_here"),
    "database": os.environ.get("MYSQL_DATABASE", "your_mysql_database_here"),
    "ssl_verify_cert": True  # Required for PlanetScale SSL
}

# -----------------------------
# PostgreSQL config (ElephantSQL / cloud)
# -----------------------------
POSTGRES_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "your_postgres_host_here"),
    "user": os.environ.get("POSTGRES_USER", "your_postgres_user_here"),
    "password": os.environ.get("POSTGRES_PASSWORD", "your_postgres_password_here"),
    "database": os.environ.get("POSTGRES_DATABASE", "your_postgres_database_here"),
    "sslmode": "require"  # Required for cloud PostgreSQL
}
