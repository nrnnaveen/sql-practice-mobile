"""
Query validation utilities.

Provides SQL injection prevention, dangerous-pattern detection, and basic
query hygiene checks before queries are sent to the database engines.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns that indicate likely SQL injection or destructive intent
# ---------------------------------------------------------------------------
_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # Stacked / multiple statements (often used to smuggle additional SQL)
    (r";\s*(?:drop|truncate|delete|insert|update|create|alter|grant|revoke)\b",
     "Multiple stacked statements are not allowed"),
    # Comment-based injection (inline comment after legit code)
    (r"(?:--|#)\s*\b(?:or|and)\b",
     "Comment-based injection pattern detected"),
    # UNION-based injection with suspicious column count manipulation
    (r"\bunion\s+(?:all\s+)?select\b.*\bnull\b.*\bnull\b",
     "UNION-based injection pattern detected"),
    # Blind injection: always-true / always-false tautologies
    (r"\b(?:or|and)\s+(?:'[^']*'\s*=\s*'[^']*'|\"[^\"]*\"\s*=\s*\"[^\"]*\"|\d+\s*=\s*\d+)",
     "Tautology-based injection pattern detected"),
    # xp_cmdshell and other SQL Server dangerous procs
    (r"\bxp_\w+\b",
     "Extended stored procedures are not allowed"),
    # EXEC / sp_executesql (dynamic SQL execution)
    (r"\bexec(?:ute)?\s*\(",
     "Dynamic SQL execution is not allowed"),
    (r"\bsp_executesql\b",
     "Dynamic SQL execution is not allowed"),
    # pg_sleep / SLEEP-based timing attacks
    (r"\b(?:pg_sleep|sleep)\s*\(",
     "Time-based blind injection pattern detected"),
    # File I/O: LOAD DATA / OUTFILE / DUMPFILE
    (r"\b(?:load\s+data|into\s+outfile|into\s+dumpfile)\b",
     "File I/O statements are not allowed"),
    # INFORMATION_SCHEMA / system catalog access with injected UNION
    (r"union\s+.*information_schema",
     "Schema enumeration via UNION is not allowed"),
]

_COMPILED: list[tuple[re.Pattern, str]] = [
    (re.compile(pat, re.IGNORECASE | re.DOTALL), msg)
    for pat, msg in _DANGEROUS_PATTERNS
]

# Maximum query length (characters) to prevent resource-exhaustion payloads
MAX_QUERY_LENGTH = 8_000


def validate_query(query: str) -> Optional[str]:
    """
    Inspect *query* for dangerous patterns and basic hygiene issues.

    Returns ``None`` when the query passes all checks, or a human-readable
    error string that should be shown to the user.
    """
    if not query or not query.strip():
        return "Query must not be empty."

    if len(query) > MAX_QUERY_LENGTH:
        return f"Query is too long (max {MAX_QUERY_LENGTH} characters)."

    for pattern, message in _COMPILED:
        if pattern.search(query):
            logger.warning("Blocked query – %s: %.200s", message, query)
            return f"Query rejected: {message}."

    return None


def sanitize_identifier(name: str) -> str:
    """
    Return *name* with only alphanumeric characters and underscores, capped at
    64 characters.  Intended for table/column names used in dynamic SQL inside
    the application itself (NOT user-supplied table names).
    """
    sanitized = re.sub(r"[^\w]", "_", name)[:64]
    return sanitized
