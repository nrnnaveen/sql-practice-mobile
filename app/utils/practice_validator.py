"""Practice mode answer validator.

Compares a user's query result against the expected sample answer by:
1. Checking query types match (e.g. SELECT vs SELECT)
2. For SELECT queries: running the expected query and comparing columns/rows
3. For DDL/DML queries: accepting any successful execution if query type matches
"""
import logging

logger = logging.getLogger(__name__)

_SELECT_TYPES = {"SELECT"}
_DDL_TYPES = {"CREATE", "ALTER", "DROP"}
_DML_TYPES = {"INSERT", "UPDATE", "DELETE"}


def validate_practice_answer(
    user_result: dict,
    user_query: str,
    question: dict,
    sandbox_db: dict,
    run_query_fn,
) -> dict:
    """Validate a user's practice query against the expected sample answer.

    Parameters
    ----------
    user_result:
        The dict returned by ``_run_sandbox_query`` for the user's query.
    user_query:
        The raw SQL string the user submitted.
    question:
        The question dict (must have ``sample_answer`` key).
    sandbox_db:
        The user's sandbox database connection info.
    run_query_fn:
        Callable ``(sandbox_db, sql) -> dict`` used to execute the sample answer.

    Returns
    -------
    dict with keys: ``is_correct`` (bool), ``feedback`` (str)
    """
    if user_result.get("error"):
        return {"is_correct": False, "feedback": f"Query error: {user_result['error']}"}

    sample_answer = (question.get("sample_answer") or "").strip()
    if not sample_answer:
        # No expected answer to compare – accept any successful result
        return {"is_correct": True, "feedback": "Query executed successfully!"}

    from app.services.query_parser_service import parse_query_type

    user_qtype = parse_query_type(user_query)
    expected_qtype = parse_query_type(sample_answer)

    # Query type must match (e.g. can't answer SELECT question with INSERT)
    if user_qtype != expected_qtype:
        return {
            "is_correct": False,
            "feedback": (
                f"Wrong query type. Expected a {expected_qtype} query, "
                f"but got {user_qtype}."
            ),
        }

    # For DDL/DML queries, accept any successful execution of the correct type
    if user_qtype in _DDL_TYPES | _DML_TYPES:
        return {"is_correct": True, "feedback": "Query executed successfully!"}

    # For SELECT queries, run the sample answer and compare results
    if user_qtype in _SELECT_TYPES:
        try:
            expected_result = run_query_fn(sandbox_db, sample_answer)
        except Exception as exc:
            logger.warning("Could not run sample answer for validation: %s", exc)
            # If we can't run expected, fall back to accepting any result
            return {"is_correct": True, "feedback": "Query executed successfully!"}

        if expected_result.get("error"):
            # Sample answer failed (DB state issue) – accept user's result
            return {"is_correct": True, "feedback": "Query executed successfully!"}

        # Compare columns (case-insensitive, order-independent)
        user_cols = [c.lower() for c in (user_result.get("columns") or [])]
        exp_cols = [c.lower() for c in (expected_result.get("columns") or [])]

        if set(user_cols) != set(exp_cols):
            missing = sorted(set(exp_cols) - set(user_cols))
            extra = sorted(set(user_cols) - set(exp_cols))
            msgs = []
            if missing:
                msgs.append(f"Missing column(s): {', '.join(missing)}")
            if extra:
                msgs.append(f"Unexpected column(s): {', '.join(extra)}")
            return {"is_correct": False, "feedback": ". ".join(msgs) or "Column mismatch."}

        # Compare row counts
        user_rows = user_result.get("rows") or []
        exp_rows = expected_result.get("rows") or []

        if len(user_rows) != len(exp_rows):
            return {
                "is_correct": False,
                "feedback": (
                    f"Expected {len(exp_rows)} row(s) but got {len(user_rows)}. "
                    "Check your WHERE clause or filters."
                ),
            }

        return {"is_correct": True, "feedback": "Correct! Well done."}

    # For OTHER query types, accept any successful result
    return {"is_correct": True, "feedback": "Query executed successfully!"}
