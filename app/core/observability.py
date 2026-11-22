"""
Structured JSON Logging & Lightweight Rate Limiting for Cloud Run Observability.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, Tuple

logger = logging.getLogger("geo_oracle_x402")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False


def log_event(event: str, severity: str = "INFO", **fields: Any) -> None:
    """Emits a single-line JSON log record compatible with Google Cloud Logging."""
    record = {
        "severity": severity.upper(),
        "event": event,
        "timestamp": int(time.time()),
        **fields,
    }
    level = getattr(logging, severity.upper(), logging.INFO)
    logger.log(level, json.dumps(record, default=str, ensure_ascii=False))


class SlidingWindowRateLimiter:
    """Thread-safe per-key sliding-window rate limiter (requests per 60s window)."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._buckets: Dict[str, Deque[float]] = {}

    def check(self, key: str) -> Tuple[bool, int, int]:
        """Returns (allowed, remaining, retry_after_seconds)."""
        if self.max_requests <= 0:
            return True, -1, 0

        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])) + 1)
                return False, 0, retry_after

            bucket.append(now)
            remaining = max(0, self.max_requests - len(bucket))
            return True, remaining, 0

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
