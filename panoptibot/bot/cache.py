from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, TypeVar

T = TypeVar('T')


def cached(maxsize: int = 128) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Simple cache decorator. Wraps functools.lru_cache."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        return lru_cache(maxsize=maxsize)(func)
    return decorator


# Global cache for Discord objects - used by resolver
# ponytail: simple lru_cache wrapper, extend if memory pressure matters
