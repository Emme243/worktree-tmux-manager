"""Tests for modules.github.cache — CachedGitHubClient."""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.github.cache import CachedGitHubClient
from modules.github.models import Comment, PRState, PullRequest

# --- Fixtures ---


def _make_pr(number: int = 1) -> PullRequest:
    return PullRequest(
        number=number,
        title="Test PR",
        state=PRState.OPEN,
        url="https://github.com/owner/repo/pull/1",
        head_branch="feat/test",
        base_branch="main",
        merged=False,
        draft=False,
        updated_at=dt.datetime(2025, 1, 1, tzinfo=dt.UTC),
    )


def _make_comment(comment_id: int = 1) -> Comment:
    return Comment(
        id=comment_id,
        body="looks good",
        author="alice",
        created_at=dt.datetime(2025, 1, 1, tzinfo=dt.UTC),
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    client = MagicMock()
    client.fetch_open_prs = AsyncMock(return_value=[_make_pr()])
    client.fetch_pr_comments = AsyncMock(return_value=[_make_comment()])
    client.get_pr_merge_status = AsyncMock(return_value="open")
    client.connect = AsyncMock()
    client.close = AsyncMock()
    return client


def _controllable_clock(
    start: dt.datetime | None = None,
) -> tuple[list[dt.datetime], object]:
    """Return a mutable time list and a clock callable."""
    now = [start or dt.datetime(2025, 6, 1, tzinfo=dt.UTC)]
    return now, lambda: now[0]


# --- fetch_open_prs ---


class TestFetchOpenPrsCaching:
    @pytest.mark.asyncio()
    async def test_first_call_delegates(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        result = await cached.fetch_open_prs()

        assert result == [_make_pr()]
        mock_client.fetch_open_prs.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_second_call_within_ttl_uses_cache(
        self, mock_client: MagicMock
    ) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_open_prs()
        clock[0] += dt.timedelta(seconds=10)
        result = await cached.fetch_open_prs()

        assert result == [_make_pr()]
        assert mock_client.fetch_open_prs.await_count == 1

    @pytest.mark.asyncio()
    async def test_call_after_ttl_refetches(self, mock_client: MagicMock) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_open_prs()
        clock[0] += dt.timedelta(seconds=31)
        await cached.fetch_open_prs()

        assert mock_client.fetch_open_prs.await_count == 2


# --- fetch_pr_comments ---


class TestFetchPrCommentsCaching:
    @pytest.mark.asyncio()
    async def test_cache_hit(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_pr_comments(42)
        result = await cached.fetch_pr_comments(42)

        assert result == [_make_comment()]
        assert mock_client.fetch_pr_comments.await_count == 1

    @pytest.mark.asyncio()
    async def test_cache_miss_after_ttl(self, mock_client: MagicMock) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_pr_comments(42)
        clock[0] += dt.timedelta(seconds=31)
        await cached.fetch_pr_comments(42)

        assert mock_client.fetch_pr_comments.await_count == 2

    @pytest.mark.asyncio()
    async def test_different_prs_cached_independently(
        self, mock_client: MagicMock
    ) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_pr_comments(1)
        await cached.fetch_pr_comments(2)

        assert mock_client.fetch_pr_comments.await_count == 2


# --- get_pr_merge_status ---


class TestGetPrMergeStatusCaching:
    @pytest.mark.asyncio()
    async def test_cache_hit(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.get_pr_merge_status(10)
        result = await cached.get_pr_merge_status(10)

        assert result == "open"
        assert mock_client.get_pr_merge_status.await_count == 1

    @pytest.mark.asyncio()
    async def test_different_prs_cached_independently(
        self, mock_client: MagicMock
    ) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.get_pr_merge_status(10)
        await cached.get_pr_merge_status(20)

        assert mock_client.get_pr_merge_status.await_count == 2


# --- invalidate ---


class TestInvalidate:
    @pytest.mark.asyncio()
    async def test_invalidate_specific_key(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_open_prs()
        cached.invalidate("prs:open")
        await cached.fetch_open_prs()

        assert mock_client.fetch_open_prs.await_count == 2

    @pytest.mark.asyncio()
    async def test_invalidate_all(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_open_prs()
        await cached.fetch_pr_comments(1)
        cached.invalidate()
        await cached.fetch_open_prs()
        await cached.fetch_pr_comments(1)

        assert mock_client.fetch_open_prs.await_count == 2
        assert mock_client.fetch_pr_comments.await_count == 2

    @pytest.mark.asyncio()
    async def test_invalidate_nonexistent_key_is_noop(
        self, mock_client: MagicMock
    ) -> None:
        cached = CachedGitHubClient(mock_client)
        cached.invalidate("does-not-exist")  # should not raise


# --- TTL configuration ---


class TestTTLConfig:
    @pytest.mark.asyncio()
    async def test_custom_ttl(self, mock_client: MagicMock) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, ttl_seconds=5, _clock=clock_fn)

        await cached.fetch_open_prs()
        clock[0] += dt.timedelta(seconds=6)
        await cached.fetch_open_prs()

        assert mock_client.fetch_open_prs.await_count == 2

    @pytest.mark.asyncio()
    async def test_default_ttl_is_30s(self, mock_client: MagicMock) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedGitHubClient(mock_client, _clock=clock_fn)

        await cached.fetch_open_prs()
        clock[0] += dt.timedelta(seconds=29)
        await cached.fetch_open_prs()

        assert mock_client.fetch_open_prs.await_count == 1


# --- Lifecycle delegation ---


class TestLifecycleDelegation:
    @pytest.mark.asyncio()
    async def test_connect_delegates(self, mock_client: MagicMock) -> None:
        cached = CachedGitHubClient(mock_client)
        await cached.connect()
        mock_client.connect.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_close_delegates(self, mock_client: MagicMock) -> None:
        cached = CachedGitHubClient(mock_client)
        await cached.close()
        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_context_manager(self, mock_client: MagicMock) -> None:
        async with CachedGitHubClient(mock_client) as cached:
            assert isinstance(cached, CachedGitHubClient)
        mock_client.connect.assert_awaited_once()
        mock_client.close.assert_awaited_once()
