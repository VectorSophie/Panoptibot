from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from time import monotonic


@dataclass(slots=True)
class SlidingWindowRateLimiter:
    limit: int
    window_seconds: int
    buckets: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, key: str) -> bool:
        now = monotonic()
        bucket = self.buckets[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True
