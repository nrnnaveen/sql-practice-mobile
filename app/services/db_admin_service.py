"""Per-user cloud database administration service.

Responsible for:
- Checking username availability
- Creating isolated MySQL / PostgreSQL databases for each user
- Loading sample data (employees, products, orders)
- Retrieving stored credentials

Design: one MySQL database AND one PostgreSQL database per user (both optional).
Credentials are stored encrypted in the local SQLite ``user_databases`` table.
"""
import logging
import re
import sqlite3

from app.utils.db_init import DB_PATH
from app.utils.encryption import decrypt_password, encrypt_password
from config import MYSQL_ADMIN_CONFIG, POSTGRES_ADMIN_CONFIG

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample DDL / DML loaded into every new sandbox database
# ---------------------------------------------------------------------------
_SAMPLE_SQL = [
    # employees
    """CREATE TABLE IF NOT EXISTS employees (
        id         INT PRIMARY KEY AUTO_INCREMENT,
        name       VARCHAR(100) NOT NULL,
        department VARCHAR(100),
        salary     DECIMAL(10,2),
        hire_date  DATE
    )""",
    """INSERT INTO employees (name, department, salary, hire_date) VALUES
        ('Alice Johnson',  'Engineering', 95000.00, '2020-03-15'),
        ('Bob Smith',      'Marketing',   72000.00, '2019-07-01'),
        ('Carol White',    'Engineering', 105000.00,'2018-01-20'),
        ('David Brown',    'HR',          65000.00, '2021-11-05'),
        ('Eve Davis',      'Engineering', 88000.00, '2022-02-28'),
        ('Frank Wilson',   'Marketing',   78000.00, '2020-09-10'),
        ('Grace Lee',      'Finance',     90000.00, '2017-05-22'),
        ('Henry Taylor',   'Engineering', 112000.00,'2016-12-01'),
        ('Irene Martinez', 'HR',          67000.00, '2023-04-15'),
        ('Jack Anderson',  'Finance',     95000.00, '2019-03-30')""",
    # products
    """CREATE TABLE IF NOT EXISTS products (
        id          INT PRIMARY KEY AUTO_INCREMENT,
        name        VARCHAR(200) NOT NULL,
        category    VARCHAR(100),
        price       DECIMAL(10,2),
        stock       INT DEFAULT 0
    )""",
    """INSERT INTO products (name, category, price, stock) VALUES
        ('Laptop Pro 15',      'Electronics', 1299.99, 45),
        ('Wireless Mouse',     'Electronics',   29.99,200),
        ('USB-C Hub',          'Electronics',   49.99,150),
        ('Standing Desk',      'Furniture',    599.99, 30),
        ('Ergonomic Chair',    'Furniture',    449.99, 25),
        ('Monitor 27"',        'Electronics',  379.99, 60),
        ('Mechanical Keyboard','Electronics',   89.99,100),
        ('Webcam HD',          'Electronics',   79.99, 80),
        ('Desk Lamp',          'Furniture',     39.99,120),
        ('Notepad Bundle',     'Stationery',     9.99,500)""",
    # orders
    """CREATE TABLE IF NOT EXISTS orders (
        id           INT PRIMARY KEY AUTO_INCREMENT,
        employee_id  INT,
        product_id   INT,
        quantity     INT DEFAULT 1,
        total_price  DECIMAL(10,2),
        order_date   DATE,
        FOREIGN KEY (employee_id) REFERENCES employees(id),
        FOREIGN KEY (product_id)  REFERENCES products(id)
    )""",
    """INSERT INTO orders (employee_id, product_id, quantity, total_price, order_date) VALUES
        (1, 1, 1, 1299.99, '2024-01-15'),
        (2, 2, 2,   59.98, '2024-01-20'),
        (3, 4, 1,  599.99, '2024-02-01'),
        (4, 5, 1,  449.99, '2024-02-10'),
        (5, 3, 3,  149.97, '2024-02-15'),
        (1, 6, 1,  379.99, '2024-03-01'),
        (6, 7, 1,   89.99, '2024-03-05'),
        (7, 8, 2,  159.98, '2024-03-10'),
        (8, 9, 1,   39.99, '2024-03-15'),
        (9,10, 5,   49.95, '2024-03-20')""",
]

# PostgreSQL-flavoured DDL (AUTO_INCREMENT → SERIAL, etc.)
_SAMPLE_SQL_PG = [
    sql.replace("AUTO_INCREMENT", "").replace("INT PRIMARY KEY", "SERIAL PRIMARY KEY")
    for sql in _SAMPLE_SQL
]

# Allowed chars for custom username: lowercase letters, digits, underscore, 3-30 chars
_USERNAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,29}$")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_username_available(db_type: str, username: str) -> bool:
    """Return *True* if *username* is not already taken in the cloud database."""
    if not _USERNAME_RE.match(username):
        return False
    try:
        if db_type == "mysql":
            return _mysql_username_available(username)
        elif db_type == "postgres":
            return _pg_username_available(username)
    except Exception as exc:
        logger.error("Error checking username availability (%s): %s", db_type, exc)
    return False


def create_user_database(user_id: int, db_type: str, username: str, password: str) -> dict:
    """Create an isolated database for *user_id* and return connection info.

    Returns a dict with keys: ``db_name``, ``db_user``, ``db_host``,
    ``db_port``, ``db_type``.  Raises ``ValueError`` on validation failure and
    ``RuntimeError`` on infrastructure errors.

    Each user may have one MySQL AND one PostgreSQL database.  Attempting to
    create a second database of the *same* type raises ``ValueError``.
    """
    # --- validate inputs ---
    if not _USERNAME_RE.match(username):
        raise ValueError(
            "Username must be 3–30 characters, start with a letter, "
            "and contain only lowercase letters, digits, and underscores."
        )
    if len(password) < 8:
        raise ValueError("Database password must be at least 8 characters.")

    if db_type not in ("mysql", "postgres"):
        raise ValueError("Unsupported database type. Choose 'mysql' or 'postgres'.")

    # Ensure username not already taken
    if not is_username_available(db_type, username):
        raise ValueError(f"Username '{username}' is already taken. Please choose another.")

    db_name = f"sandbox_{username}"

    try:
        if db_type == "mysql":
            info = _create_mysql_db(db_name, username, password)
        else:
            info = _create_pg_db(db_name, username, password)
    except Exception as exc:
        logger.error("Failed to create database for user %d: %s", user_id, exc)
        raise RuntimeError(f"Database creation failed: {exc}") from exc

    # Persist encrypted credentials in user_databases table
    _store_credentials(user_id, db_type, db_name, username, password, info["host"], info["port"])

    return {
        "db_type": db_type,
        "db_name": db_name,
        "db_user": username,
        "db_host": info["host"],
        "db_port": info["port"],
    }


def get_user_db_info(user_id: int, db_type: str = None) -> dict | None:
    """Return connection info for *user_id*'s sandbox database, or *None*.

    If *db_type* is given, returns info for that specific type ('mysql' or
    'postgres').  If *db_type* is ``None``, returns the first database found
    (mysql preferred) for backward compatibility.

    The returned dict includes ``db_type``, ``db_name``, ``db_user``,
    ``db_host``, ``db_port``, and ``db_password`` (decrypted).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        if db_type:
            row = conn.execute(
                "SELECT db_type, db_name, db_user, db_password, db_host, db_port "
                "FROM user_databases WHERE user_id = ? AND db_type = ?",
                (user_id, db_type),
            ).fetchone()
        else:
            # Return the first available (mysql preferred)
            row = conn.execute(
                "SELECT db_type, db_name, db_user, db_password, db_host, db_port "
                "FROM user_databases WHERE user_id = ? "
                "ORDER BY CASE db_type WHEN 'mysql' THEN 0 ELSE 1 END LIMIT 1",
                (user_id,),
            ).fetchone()
        conn.close()
        if not row:
            return None
        return {
            "db_type": row["db_type"],
            "db_name": row["db_name"],
            "db_user": row["db_user"],
            "db_host": row["db_host"],
            "db_port": row["db_port"],
            "db_password": decrypt_password(row["db_password"]),
        }
    except Exception as exc:
        logger.error("Error fetching DB info for user %d: %s", user_id, exc)
        return None


def get_all_user_dbs(user_id: int) -> dict:
    """Return a dict with keys 'mysql' and 'postgres', each being the
    connection-info dict (or ``None``) for the respective database type.
    """
    return {
        "mysql": get_user_db_info(user_id, "mysql"),
        "postgres": get_user_db_info(user_id, "postgres"),
    }


# ---------------------------------------------------------------------------
# Internal MySQL helpers
# ---------------------------------------------------------------------------

def _mysql_conn(cfg: dict):
    import mysql.connector  # type: ignore
    return mysql.connector.connect(**cfg)


def _mysql_username_available(username: str) -> bool:
    import mysql.connector  # type: ignore
    conn = _mysql_conn(MYSQL_ADMIN_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM mysql.user WHERE User = %s", (username,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count == 0


def _create_mysql_db(db_name: str, username: str, password: str) -> dict:
    """Create *db_name* database and *username* user, load sample data.

    Both *db_name* and *username* are validated by _USERNAME_RE before this
    function is called (lowercase alphanumeric + underscore, 3–30 chars,
    must start with a letter).  MySQL does not support parameterised
    identifiers, so they are interpolated directly after validation – the
    regex ensures no SQL special characters are present.
    """
    conn = _mysql_conn(MYSQL_ADMIN_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cur.execute(
            f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED BY %s",
            (password,),
        )
        cur.execute(
            f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'%'"
        )
        cur.execute("FLUSH PRIVILEGES")
        # Load sample data
        cur.execute(f"USE `{db_name}`")
        for stmt in _SAMPLE_SQL:
            cur.execute(stmt)
    finally:
        cur.close()
        conn.close()

    cfg = MYSQL_ADMIN_CONFIG
    return {"host": cfg.get("host", "localhost"), "port": cfg.get("port", 3306)}


# ---------------------------------------------------------------------------
# Internal PostgreSQL helpers
# ---------------------------------------------------------------------------

def _pg_conn(cfg: dict):
    import psycopg2  # type: ignore
    return psycopg2.connect(**cfg)


def _pg_username_available(username: str) -> bool:
    conn = _pg_conn(POSTGRES_ADMIN_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pg_roles WHERE rolname = %s", (username,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count == 0


def _create_pg_db(db_name: str, username: str, password: str) -> dict:
    """Create *db_name* database and *username* role, load sample data.

    Uses ``psycopg2.sql.Identifier`` to safely quote identifiers, which
    prevents SQL injection even if the validation logic is ever changed.
    """
    from psycopg2 import sql as pgsql  # type: ignore

    conn = _pg_conn(POSTGRES_ADMIN_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(
            pgsql.SQL("CREATE USER {} WITH PASSWORD %s").format(pgsql.Identifier(username)),
            (password,),
        )
        cur.execute(
            pgsql.SQL("CREATE DATABASE {} OWNER {}").format(
                pgsql.Identifier(db_name), pgsql.Identifier(username)
            )
        )
    finally:
        cur.close()
        conn.close()

    # Connect to the new database to load sample data
    user_cfg = dict(POSTGRES_ADMIN_CONFIG)
    user_cfg["database"] = db_name
    conn2 = _pg_conn(user_cfg)
    conn2.autocommit = False
    cur2 = conn2.cursor()
    try:
        for stmt in _SAMPLE_SQL_PG:
            cur2.execute(stmt)
        conn2.commit()
    except Exception:
        conn2.rollback()
        raise
    finally:
        cur2.close()
        conn2.close()

    # Grant privileges
    conn3 = _pg_conn(POSTGRES_ADMIN_CONFIG)
    conn3.autocommit = True
    cur3 = conn3.cursor()
    try:
        cur3.execute(
            pgsql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                pgsql.Identifier(db_name), pgsql.Identifier(username)
            )
        )
    finally:
        cur3.close()
        conn3.close()

    cfg = POSTGRES_ADMIN_CONFIG
    return {"host": cfg.get("host", "localhost"), "port": cfg.get("port", 5432)}


# ---------------------------------------------------------------------------
# Credential persistence
# ---------------------------------------------------------------------------

def _store_credentials(
    user_id: int,
    db_type: str,
    db_name: str,
    username: str,
    password: str,
    host: str,
    port: int,
) -> None:
    encrypted = encrypt_password(password)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT OR REPLACE INTO user_databases
           (user_id, db_type, db_name, db_user, db_password, db_host, db_port)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, db_type, db_name, username, encrypted, host, port),
    )
    conn.commit()
    conn.close()
    logger.info("Stored sandbox DB credentials for user %d (%s@%s)", user_id, username, db_name)
