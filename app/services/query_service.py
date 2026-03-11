"""
Query execution service.

Wraps the low-level MySQL / PostgreSQL engine calls with:

* **Input validation** via ``app.utils.validators``
* **30-second timeout** using a background thread
* **Result pagination** (100 rows per page)
* **Execution statistics** (elapsed time)
* **Caching** via ``app.services.cache_service``
"""

import logging
import time
import threading
from typing import Any

from app.utils.validators import validate_query
from app.services.cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)

PAGE_SIZE = 100  # rows per page


def _run_in_thread(fn, *args, timeout: float = 30.0) -> dict[str, Any]:
    """
    Execute *fn(*args)* in a daemon thread and wait up to *timeout* seconds.
    Returns the function's result, or an error dict on timeout / exception.
    """
    result: dict[str, Any] = {}
    exc_holder: list[Exception] = []

    def target():
        try:
            result.update(fn(*args))
        except Exception as exc:  # noqa: BLE001 – we intentionally catch all DB/timeout errors here
            exc_holder.append(exc)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return {"error": f"Query timed out after {int(timeout)} seconds."}
    if exc_holder:
        return {"error": str(exc_holder[0])}
    return result


def execute_query(
    query: str,
    db_type: str,
    page: int = 1,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Validate and execute *query* against the database identified by *db_type*
    (``"mysql"`` or ``"postgres"``).

    Parameters
    ----------
    query:
        Raw SQL string from the user.
    db_type:
        Target database engine (``"mysql"`` or ``"postgres"``).
    page:
        1-based page number for paginated results (default 1).
    use_cache:
        Whether to consult the in-process cache for SELECT queries.

    Returns
    -------
    dict with keys:

    * ``columns`` + ``rows`` + ``total_rows`` + ``page`` + ``total_pages``
      for SELECT queries.
    * ``message`` for non-SELECT queries.
    * ``error`` on failure.
    * ``elapsed_ms`` always present.
    * ``cached`` (bool) – True when the result came from the cache.
    """
    # ── Validate ────────────────────────────────────────────────────────────
    validation_error = validate_query(query)
    if validation_error:
        return {"error": validation_error, "elapsed_ms": 0}

    # ── Cache lookup (SELECT only) ───────────────────────────────────────────
    is_select = query.strip().lower().startswith("select")
    cache_key = f"{db_type}:{hash(query)}"
    if is_select and use_cache:
        cached = cache_get(cache_key)
        if cached is not None:
            cached["cached"] = True
            cached["page"] = page
            # Re-slice the page from full cached rows
            all_rows = cached.get("_all_rows", cached.get("rows", []))
            cached["rows"], cached["total_pages"] = _paginate(all_rows, page)
            cached["total_rows"] = len(all_rows)
            return cached

    # ── Execute ──────────────────────────────────────────────────────────────
    start = time.perf_counter()

    if db_type == "mysql":
        from app.services.mysql_service import run_mysql
        raw = _run_in_thread(run_mysql, query)
    elif db_type == "postgres":
        from app.services.postgres_service import run_postgres
        raw = _run_in_thread(run_postgres, query)
    else:
        return {"error": f"Unknown database type: {db_type}", "elapsed_ms": 0}

    elapsed_ms = round((time.perf_counter() - start) * 1000)
    raw["elapsed_ms"] = elapsed_ms
    raw["cached"] = False

    # ── Paginate ─────────────────────────────────────────────────────────────
    if "error" not in raw and "columns" in raw:
        all_rows: list = raw.get("rows", [])
        page_rows, total_pages = _paginate(all_rows, page)
        raw["_all_rows"] = all_rows  # kept for cache but not sent to template
        raw["rows"] = page_rows
        raw["total_rows"] = len(all_rows)
        raw["total_pages"] = total_pages
        raw["page"] = page

        # Store in cache (only successful SELECT results)
        if is_select and use_cache:
            cache_set(cache_key, raw)

    logger.info(
        "Query executed db=%s elapsed_ms=%d rows=%s",
        db_type,
        elapsed_ms,
        raw.get("total_rows", "N/A"),
    )
    return raw


def _paginate(rows: list, page: int) -> tuple[list, int]:
    """Slice *rows* for the requested *page* and return (page_rows, total_pages)."""
    total = len(rows)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    return rows[start: start + PAGE_SIZE], total_pages
