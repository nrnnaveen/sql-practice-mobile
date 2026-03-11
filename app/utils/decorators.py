"""
Custom Flask decorators.

- ``login_required``  – redirect to /login when the user is not authenticated.
- ``rate_limit``      – per-user in-process rate limiter (no Redis dependency).
"""

import time
import logging
import threading
from collections import deque
from functools import wraps
from typing import Callable

from flask import redirect, session, jsonify, request

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process rate-limit store: {user_id: deque[timestamp]}
# Protected by a lock so concurrent requests don't corrupt counts.
# ---------------------------------------------------------------------------
_rate_store: dict[str, deque] = {}
_rate_lock = threading.Lock()


def login_required(f: Callable) -> Callable:
    """Redirect to /login if the session has no ``user_id``."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


def rate_limit(max_requests: int = 10, window_seconds: int = 60) -> Callable:
    """
    Decorator factory.  Allows up to *max_requests* calls per *window_seconds*
    per authenticated user (keyed on ``session["user_id"]``).

    For unauthenticated requests the check is skipped (login_required should
    handle those first).

    On limit breach returns HTTP 429 JSON for AJAX and a plain error string
    for form submissions.
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_id = session.get("user_id")
            if user_id is None:
                return f(*args, **kwargs)

            key = str(user_id)
            now = time.monotonic()
            cutoff = now - window_seconds

            with _rate_lock:
                bucket = _rate_store.setdefault(key, deque())
                # Evict timestamps outside the sliding window
                while bucket and bucket[0] < cutoff:
                    bucket.popleft()
                if len(bucket) >= max_requests:
                    logger.warning(
                        "Rate limit exceeded for user %s (%d/%d in %ds)",
                        user_id, len(bucket), max_requests, window_seconds,
                    )
                    is_ajax = (
                        request.headers.get("X-Requested-With") == "XMLHttpRequest"
                        or request.is_json
                    )
                    if is_ajax:
                        return jsonify({
                            "error": f"Rate limit exceeded: max {max_requests} queries per {window_seconds}s."
                        }), 429
                    # Re-render the original view with an error flag
                    return f(*args, _rate_limited=True, **kwargs)
                bucket.append(now)

            return f(*args, **kwargs)
        return wrapped
    return decorator
