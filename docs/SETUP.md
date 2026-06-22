# Setup Guide – SQL Practice Mobile

## Overview

SQL Practice Mobile uses a **two-tier database architecture**:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| User accounts | SQLite (`database/users.db`) | Authentication, settings, query history |
| Sandbox databases | MySQL or PostgreSQL (cloud) | Per-user isolated SQL practice environment |

---

## Prerequisites

- Python 3.11+
- MySQL 8+ **or** PostgreSQL 14+ (cloud instance)
- (Optional) Google Cloud project for OAuth

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/nrnnaveen/sql-practice-mobile
cd sql-practice-mobile
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your values (see below)

# 3. Run
flask run
# or: gunicorn "app:create_app()"
```

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask session secret (random 32+ chars) |
| `CIPHER_KEY` | Fernet key for encrypting DB passwords (see below) |

### MySQL (for sandbox databases)

| Variable | Default | Description |
|----------|---------|-------------|
| `MYSQL_ADMIN_HOST` | `MYSQL_HOST` | Admin DB host |
| `MYSQL_ADMIN_USER` | `MYSQL_USER` | Admin user (needs CREATE USER/DB/GRANT) |
| `MYSQL_ADMIN_PASSWORD` | `MYSQL_PASSWORD` | Admin password |

### PostgreSQL (alternative)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_ADMIN_URL` | — | Full psql URL for admin connection |
| `POSTGRES_ADMIN_USER` | `POSTGRES_USER` | Superuser login |
| `POSTGRES_ADMIN_PASSWORD` | `POSTGRES_PASSWORD` | Superuser password |

### Google OAuth (optional)

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret |

---

## Generating a CIPHER_KEY

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output into your `.env` as `CIPHER_KEY=...`.

---

## MySQL Admin Account Setup

The admin account must be able to create users and databases:

```sql
-- Run as root / superuser
GRANT CREATE USER, CREATE ON *.* TO 'admin_user'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

---

## PostgreSQL Admin Setup

The admin account must be a superuser (or have CREATEROLE + CREATEDB):

```sql
-- Run as postgres superuser
CREATE USER admin_user WITH PASSWORD 'secret' CREATEROLE CREATEDB;
```

---

## Running Tests

```bash
pytest
```
