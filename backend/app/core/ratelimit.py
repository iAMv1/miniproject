"""MindPulse — Minimal in-memory sliding-window rate limiter.

No external dependency: a fixed-size per-key deque of request timestamps.
Sufficient for single-process deployments. Replace with a shared store
(Redis) when scaling horizontally.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Optional

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        ip = "unknown"
    auth = request.headers.get("authorization", "")
    return f"{ip}:{auth}"


def rate_limit(limiter: SlidingWindowLimiter) -> Callable:
    def dependency(request: Request) -> None:
        if not limiter.check(_client_key(request)):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Try again later.",
            )

    return dependency
