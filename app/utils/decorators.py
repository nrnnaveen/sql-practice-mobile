"""Custom decorators for the SQL Practice app.

Provides:
- ``rate_limit``: Simple in-process rate limiter (10 req/min per IP).
- ``login_required``: Redirect to login if no active session.
"""
import time
import logging
from collections import defaultdict
from functools import wraps

from flask import jsonify, redirect, request, session, url_for

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process rate limiting  (per-IP, sliding window)
# ---------------------------------------------------------------------------
# Stores a list of timestamps (epoch seconds) for each IP address.
# NOTE: This is a per-process counter. In multi-worker deployments (e.g.
# Gunicorn with 2+ workers) each worker maintains its own memory, so the
# effective limit is RATE_LIMIT_REQUESTS × workers.  For strict distributed
# rate limiting in production, replace this with a Redis-backed solution.
_request_log: dict[str, list[float]] = defaultdict(list)

RATE_LIMIT_REQUESTS = 10   # max requests
RATE_LIMIT_WINDOW = 60     # seconds


def rate_limit(f):
    """
    Decorator that limits callers to ``RATE_LIMIT_REQUESTS`` requests per
    ``RATE_LIMIT_WINDOW`` seconds, keyed by the client's remote IP address.

    On violation the decorated view returns a JSON 429 response.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr or "unknown"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # Purge timestamps outside the sliding window
        _request_log[ip] = [t for t in _request_log[ip] if t > window_start]

        if len(_request_log[ip]) >= RATE_LIMIT_REQUESTS:
            logger.warning("Rate limit exceeded for IP %s on %s", ip, request.path)
            return jsonify({
                "error": "Rate limit exceeded. Please wait before sending more queries."
            }), 429

        _request_log[ip].append(now)
        return f(*args, **kwargs)

    return decorated


def login_required(f):
    """Redirect unauthenticated requests to the login page."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated
