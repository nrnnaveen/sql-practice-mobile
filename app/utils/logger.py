"""
Logging configuration.

Provides ``configure_logging()`` which switches the root logger to emit
structured JSON lines – useful for log aggregators (Railway, Datadog, etc.).
In development the plain format from ``create_app()`` is used instead.
"""

import json
import logging
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON object on one line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """
    Replace the root logger's handlers with a single JSON-line handler on
    stdout.  Call this from ``create_app()`` when running in production
    (``FLASK_DEBUG != "1"``).
    """
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
