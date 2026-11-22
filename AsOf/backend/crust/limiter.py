"""Async token buckets per endpoint group."""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

RATES_PER_MIN = {"enrich": 15, "person": 15, "search": 30, "job": 30, "web": 10, "watch": 10}


class TokenBucket:
    def __init__(self, per_min: float, capacity: float | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], Awaitable] = asyncio.sleep):
        self.rate = per_min / 60.0
        self.capacity = capacity if capacity is not None else per_min
        self.tokens = self.capacity
        self.clock, self.sleep = clock, sleep
        self.last = clock()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = self.clock()
                self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
                self.last = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                await self.sleep((1 - self.tokens) / self.rate)


class RateLimiter:
    def __init__(self, rates: dict[str, float] | None = None, capacity: float | None = None, **kw):
        self.buckets = {g: TokenBucket(r, capacity, **kw) for g, r in (rates or RATES_PER_MIN).items()}

    async def acquire(self, group: str | None) -> None:
        b = self.buckets.get(group or "")
        if b:
            await b.acquire()
