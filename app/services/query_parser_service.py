"""Query parser service – determines the SQL operation type for animations."""
import re


# Recognised operation types
SELECT = "SELECT"
INSERT = "INSERT"
UPDATE = "UPDATE"
DELETE = "DELETE"
CREATE = "CREATE"
ALTER  = "ALTER"
DROP   = "DROP"
OTHER  = "OTHER"


def parse_query_type(sql: str) -> str:
    """Return the uppercase SQL operation type for *sql*.

    Strips leading comments/whitespace before inspecting the first keyword so
    that attempts to bypass the check via comment injection are handled
    gracefully.
    """
    if not sql or not sql.strip():
        return OTHER

    # Strip single-line (-- …) and multi-line (/* … */) comments
    cleaned = re.sub(r"--[^\n]*", " ", sql)
    cleaned = re.sub(r"/\*.*?\*/", " ", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    first_token = cleaned.split()[0].upper() if cleaned.split() else ""

    mapping = {
        "SELECT": SELECT,
        "INSERT": INSERT,
        "UPDATE": UPDATE,
        "DELETE": DELETE,
        "CREATE": CREATE,
        "ALTER":  ALTER,
        "DROP":   DROP,
        "TRUNCATE": "TRUNCATE",
        "SHOW":   OTHER,
        "DESCRIBE": OTHER,
        "DESC":   OTHER,
        "EXPLAIN": OTHER,
        "WITH":   SELECT,   # CTEs usually start with WITH … SELECT
    }
    return mapping.get(first_token, OTHER)
