"""In-memory TTL cache for GitHub API responses."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Generic, TypeVar

from modules.github.client import GitHubClient
from modules.github.models import Comment, PullRequest

__all__ = ["CachedGitHubClient"]

T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    """A cached value with its fetch timestamp."""

    data: T
    fetched_at: dt.datetime


class CachedGitHubClient:
    """Wrapper around :class:`GitHubClient` that caches responses.

    Repeated calls within the TTL window return cached data without
    hitting the GitHub API.  Use :meth:`invalidate` to force a refresh.

    Usage::

        client = GitHubClient(token, slug)
        async with CachedGitHubClient(client, ttl_seconds=30) as cached:
            prs = await cached.fetch_open_prs()
    """

    def __init__(
        self,
        client: GitHubClient,
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

    async def fetch_open_prs(self) -> list[PullRequest]:
        """Fetch open PRs, returning cached data if still fresh."""
        cache_key = "prs:open"
        if self._is_fresh(cache_key):
            return self._get(cache_key)
        data = await self._client.fetch_open_prs()
        self._put(cache_key, data)
        return data

    async def fetch_pr_comments(self, pr_number: int) -> list[Comment]:
        """Fetch PR comments, returning cached data if still fresh."""
        cache_key = f"comments:{pr_number}"
        if self._is_fresh(cache_key):
            return self._get(cache_key)
        data = await self._client.fetch_pr_comments(pr_number)
        self._put(cache_key, data)
        return data

    async def get_pr_merge_status(self, pr_number: int) -> str:
        """Get PR merge status, returning cached data if still fresh."""
        cache_key = f"merge_status:{pr_number}"
        if self._is_fresh(cache_key):
            return self._get(cache_key)
        data = await self._client.get_pr_merge_status(pr_number)
        self._put(cache_key, data)
        return data

    # -- Lifecycle delegation --

    async def connect(self) -> None:
        """Delegate to the wrapped client."""
        await self._client.connect()

    async def close(self) -> None:
        """Delegate to the wrapped client."""
        await self._client.close()

    async def __aenter__(self) -> CachedGitHubClient:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
