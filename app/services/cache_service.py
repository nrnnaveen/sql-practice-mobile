"""
Simple in-process LRU cache with TTL.

No external dependencies (no Redis required).  Suitable for caching
frequently executed SELECT queries within a single process.
"""

import time
import threading
import logging
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CACHE_TTL = 300          # seconds a cached item stays valid
_CACHE_MAX_SIZE = 256     # maximum number of entries

_store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
_lock = threading.Lock()


def cache_get(key: str) -> Optional[Any]:
    """Return the cached value for *key*, or ``None`` if absent / expired."""
    with _lock:
        if key not in _store:
            return None
        value, expires_at = _store[key]
        if time.monotonic() > expires_at:
            del _store[key]
            return None
        # Move to end (LRU: most recently used)
        _store.move_to_end(key)
        return value


def cache_set(key: str, value: Any, ttl: int = _CACHE_TTL) -> None:
    """Store *value* under *key* with the given TTL (seconds)."""
    with _lock:
        if key in _store:
            _store.move_to_end(key)
        _store[key] = (value, time.monotonic() + ttl)
        if len(_store) > _CACHE_MAX_SIZE:
            evicted_key, _ = _store.popitem(last=False)
            logger.debug("Cache evicted key: %s", evicted_key)


def cache_delete(key: str) -> None:
    """Remove *key* from the cache if present."""
    with _lock:
        _store.pop(key, None)


def cache_clear() -> None:
    """Flush all cached entries."""
    with _lock:
        _store.clear()


def cache_stats() -> dict[str, int]:
    """Return current cache size."""
    with _lock:
        return {"size": len(_store), "max_size": _CACHE_MAX_SIZE}
