"""SQL query validation utilities.

Validates user-submitted queries before execution to prevent dangerous
operations in the practice environment.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Keywords that mutate or destroy schema/data – blocked in practice mode
_BLOCKED_KEYWORDS = {
    "DROP",
    "DELETE",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "INSERT",
    "UPDATE",
    "REPLACE",
    "RENAME",
    "GRANT",
    "REVOKE",
    "LOCK",
    "UNLOCK",
    "CALL",
    "EXEC",
    "EXECUTE",
    "LOAD",
    "INTO OUTFILE",
    "INTO DUMPFILE",
}

# Read-only statements allowed in practice mode
_ALLOWED_PREFIXES = (
    "select",
    "show",
    "describe",
    "desc",
    "explain",
    "with",  # CTEs (usually for SELECT)
    "pragma",  # SQLite info queries
)

MAX_QUERY_LENGTH = 5000  # characters


def validate_query(query: str) -> tuple[bool, str]:
    """
    Validate a SQL query for safety.

    Returns a ``(is_valid, error_message)`` tuple.  ``is_valid`` is ``True``
    when the query is safe to execute; ``error_message`` is empty in that case.
    """
    if not query or not query.strip():
        return False, "Query cannot be empty."

    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters."

    # Strip comments before keyword checks to prevent bypass via comments
    cleaned = _strip_sql_comments(query)

    # Normalise whitespace for reliable keyword matching
    upper = cleaned.upper()

    # Check blocked keywords – use word boundaries to avoid false positives
    for keyword in _BLOCKED_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, upper):
            logger.warning("Blocked query containing keyword '%s': %.120s", keyword, query)
            return False, (
                f"The keyword '{keyword}' is not allowed in the practice environment. "
                "Only read-only SELECT queries are permitted."
            )

    # Enforce read-only prefix
    first_token = upper.split()[0] if upper.split() else ""
    if first_token not in {p.upper() for p in _ALLOWED_PREFIXES}:
        return False, (
            "Only SELECT (and SHOW / DESCRIBE / EXPLAIN / WITH) queries are allowed "
            "in the practice environment."
        )

    return True, ""


def _strip_sql_comments(query: str) -> str:
    """Remove SQL line comments (--) and block comments (/* */)."""
    # Remove block comments
    query = re.sub(r"/\*.*?\*/", " ", query, flags=re.DOTALL)
    # Remove line comments
    query = re.sub(r"--[^\n]*", " ", query)
    return query


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Enforce a strong password policy:
    - At least 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Returns ``(is_valid, error_message)``.
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':\"\\|,.<>\/?`~]', password):
        return False, "Password must contain at least one special character."
    return True, ""
