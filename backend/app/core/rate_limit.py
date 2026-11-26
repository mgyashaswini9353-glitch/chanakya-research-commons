"""Lightweight thread-safe sliding-window rate limiter for sensitive API endpoints."""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict

from fastapi import HTTPException, Request, status

from backend.app.core.config import settings


class SlidingWindowRateLimiter:
    """In-memory per-IP sliding-window limiter (single-instance; pair with Nginx limit_req in prod)."""

    def __init__(self) -> None:
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            dq = self._buckets[key]
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= max_requests:
                retry_after = max(1, int(dq[0] + window_seconds - now) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait a moment and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            dq.append(now)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = SlidingWindowRateLimiter()


def client_ip_from_request(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_dependency(
    scope: str,
    max_requests: int,
    window_seconds: int = 60,
) -> Callable[[Request], None]:
    """Create a FastAPI dependency enforcing `max_requests` per `window_seconds` per IP."""

    def _enforce(request: Request) -> None:
        env_mode = os.getenv("APP_ENV", settings.APP_ENV).lower()
        if env_mode == "test" and request.headers.get("x-enforce-rate-limit") != "1":
            return
        ip = client_ip_from_request(request)
        rate_limiter.check(f"{scope}:{ip}", max_requests=max_requests, window_seconds=window_seconds)

    return _enforce
