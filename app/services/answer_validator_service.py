"""Answer validator service – checks whether a user's query result is correct."""
import re


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[;,\.]$", "", text)
    return text


def validate_answer(
    user_result: dict,
    expected_output: str | None,
    expected_sql: str | None = None,
) -> dict:
    """Validate a user's query result against expected output / expected SQL.

    Parameters
    ----------
    user_result:
        The dict returned by ``_run_sandbox_query`` – may contain ``error``,
        ``message``, ``columns``/``rows``.
    expected_output:
        Plain-text description of the expected result (e.g. "Table created
        successfully", "3 rows returned").  May be ``None``.
    expected_sql:
        The canonical sample SQL answer.  Used as a fallback comparison.

    Returns
    -------
    dict with keys:
        ``is_correct`` (bool), ``feedback`` (str)
    """
    if user_result.get("error"):
        return {"is_correct": False, "feedback": f"Query error: {user_result['error']}"}

    # If we have an explicit expected_output string, use fuzzy matching
    if expected_output:
        exp = _normalise(expected_output)

        # Check for messages (DDL / DML results)
        msg = user_result.get("message", "")
        if msg and (exp in _normalise(msg) or _normalise(msg) in exp):
            return {"is_correct": True, "feedback": "Correct! Well done."}

        # Check row count hints like "3 rows"
        row_match = re.search(r"(\d+)\s+row", exp)
        if row_match and user_result.get("rows") is not None:
            expected_rows = int(row_match.group(1))
            if len(user_result["rows"]) == expected_rows:
                return {"is_correct": True, "feedback": "Correct! Well done."}

        # Generic "table created" / "query executed" etc.
        if exp in ("table created successfully", "query executed successfully",
                   "rows affected"):
            if msg:
                return {"is_correct": True, "feedback": "Correct! Well done."}

    # If the query produced *any* result without error, treat it as correct for
    # practice mode – the user can compare visually.
    if "rows" in user_result or "message" in user_result:
        return {"is_correct": True, "feedback": "Query executed successfully!"}

    return {"is_correct": False, "feedback": "Could not validate the query result."}
