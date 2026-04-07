"""In-memory TTL cache for Linear API responses."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Generic, TypeVar

from modules.linear.client import LinearClient
from modules.linear.models import Comment, Ticket

__all__ = ["CachedLinearClient"]

T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    """A cached value with its fetch timestamp."""

    data: T
    fetched_at: dt.datetime


class CachedLinearClient:
    """Wrapper around :class:`LinearClient` that caches responses.

    Repeated calls within the TTL window return cached data without
    hitting the Linear API.  Use :meth:`invalidate` to force a refresh.

    Usage::

        async with CachedLinearClient(LinearClient(api_key), ttl_seconds=30) as cached:
            tickets = await cached.fetch_my_issues(team_id)
    """

    def __init__(
        self,
        client: LinearClient,
        ttl_seconds: float = 30.0,
        _clock: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self._client = client
        self._ttl = dt.timedelta(seconds=ttl_seconds)
        self._clock = _clock or (lambda: dt.datetime.now(dt.UTC))
        self._cache: dict[str, _CacheEntry[Any]] = {}

    # -- Cache helpers --

    def _is_fresh(self, key: str) -> bool:
        entry = self._cache.get(key)
        if entry is None:
            return False
        return (self._clock() - entry.fetched_at) < self._ttl

    def _get(self, key: str) -> Any:
        return self._cache[key].data

    def _put(self, key: str, data: Any) -> None:
        self._cache[key] = _CacheEntry(data=data, fetched_at=self._clock())

    # -- Public API --

    def invalidate(self, key: str | None = None) -> None:
        """Remove a specific cache entry, or all entries if *key* is ``None``."""
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)

    async def fetch_my_issues(self, team_id: str) -> list[Ticket]:
        """Fetch issues, returning cached data if still fresh."""
        cache_key = f"issues:{team_id}"
        if self._is_fresh(cache_key):
            return self._get(cache_key)
        data = await self._client.fetch_my_issues(team_id)
        self._put(cache_key, data)
        return data

    async def fetch_issue_by_branch(self, branch: str) -> Ticket | None:
        """Fetch issue by branch, returning cached data if still fresh."""
        cache_key = f"branch:{branch}"
        if self._is_fresh(cache_key):
            return self._get(cache_key)
        data = await self._client.fetch_issue_by_branch(branch)
        self._put(cache_key, data)
        return data

    async def fetch_issue_comments(self, issue_id: str) -> list[Comment]:
        """Fetch issue comments, returning cached data if still fresh."""
        cache_key = f"comments:{issue_id}"
        if self._is_fresh(cache_key):
            return self._get(cache_key)
        data = await self._client.fetch_issue_comments(issue_id)
        self._put(cache_key, data)
        return data

    # -- Lifecycle delegation --

    async def connect(self) -> None:
        """Delegate to the wrapped client."""
        await self._client.connect()

    async def close(self) -> None:
        """Delegate to the wrapped client."""
        await self._client.close()

    async def __aenter__(self) -> CachedLinearClient:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
