"""Tests for modules.linear.cache — CachedLinearClient."""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.linear.cache import CachedLinearClient
from modules.linear.models import Comment, Ticket, TicketStatus

# --- Fixtures ---


def _make_ticket(identifier: str = "ENG-1") -> Ticket:
    return Ticket(
        id="t1",
        identifier=identifier,
        title="Test ticket",
        status=TicketStatus.IN_PROGRESS,
        branch_name="feat/test",
        url="https://linear.app/t1",
        updated_at=dt.datetime(2025, 1, 1, tzinfo=dt.UTC),
    )


def _make_comment(comment_id: str = "c1") -> Comment:
    return Comment(
        id=comment_id,
        body="hello",
        user_name="Alice",
        created_at=dt.datetime(2025, 1, 1, tzinfo=dt.UTC),
        updated_at=dt.datetime(2025, 1, 1, tzinfo=dt.UTC),
    )


@pytest.fixture()
def mock_client() -> MagicMock:
    client = MagicMock()
    client.fetch_my_issues = AsyncMock(return_value=[_make_ticket()])
    client.fetch_issue_by_branch = AsyncMock(return_value=_make_ticket())
    client.fetch_issue_comments = AsyncMock(return_value=[_make_comment()])
    client.connect = AsyncMock()
    client.close = AsyncMock()
    return client


def _controllable_clock(
    start: dt.datetime | None = None,
) -> tuple[list[dt.datetime], object]:
    """Return a mutable time list and a clock callable."""
    now = [start or dt.datetime(2025, 6, 1, tzinfo=dt.UTC)]
    return now, lambda: now[0]


# --- fetch_my_issues ---


class TestFetchMyIssuesCaching:
    @pytest.mark.asyncio()
    async def test_first_call_delegates(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        result = await cached.fetch_my_issues("team-1")

        assert result == [_make_ticket()]
        mock_client.fetch_my_issues.assert_awaited_once_with("team-1")

    @pytest.mark.asyncio()
    async def test_second_call_within_ttl_uses_cache(
        self, mock_client: MagicMock
    ) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_my_issues("team-1")
        clock[0] += dt.timedelta(seconds=10)
        result = await cached.fetch_my_issues("team-1")

        assert result == [_make_ticket()]
        assert mock_client.fetch_my_issues.await_count == 1

    @pytest.mark.asyncio()
    async def test_call_after_ttl_refetches(self, mock_client: MagicMock) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_my_issues("team-1")
        clock[0] += dt.timedelta(seconds=31)
        await cached.fetch_my_issues("team-1")

        assert mock_client.fetch_my_issues.await_count == 2

    @pytest.mark.asyncio()
    async def test_different_team_ids_cached_independently(
        self, mock_client: MagicMock
    ) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_my_issues("team-1")
        await cached.fetch_my_issues("team-2")

        assert mock_client.fetch_my_issues.await_count == 2


# --- fetch_issue_by_branch ---


class TestFetchIssueByBranchCaching:
    @pytest.mark.asyncio()
    async def test_cache_hit(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_issue_by_branch("feat/x")
        result = await cached.fetch_issue_by_branch("feat/x")

        assert result == _make_ticket()
        assert mock_client.fetch_issue_by_branch.await_count == 1

    @pytest.mark.asyncio()
    async def test_cache_miss_after_ttl(self, mock_client: MagicMock) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_issue_by_branch("feat/x")
        clock[0] += dt.timedelta(seconds=31)
        await cached.fetch_issue_by_branch("feat/x")

        assert mock_client.fetch_issue_by_branch.await_count == 2

    @pytest.mark.asyncio()
    async def test_caches_none_result(self, mock_client: MagicMock) -> None:
        mock_client.fetch_issue_by_branch.return_value = None
        _clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        r1 = await cached.fetch_issue_by_branch("no-match")
        r2 = await cached.fetch_issue_by_branch("no-match")

        assert r1 is None
        assert r2 is None
        assert mock_client.fetch_issue_by_branch.await_count == 1


# --- fetch_issue_comments ---


class TestFetchIssueCommentsCaching:
    @pytest.mark.asyncio()
    async def test_cache_hit(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_issue_comments("issue-1")
        result = await cached.fetch_issue_comments("issue-1")

        assert result == [_make_comment()]
        assert mock_client.fetch_issue_comments.await_count == 1

    @pytest.mark.asyncio()
    async def test_different_issues_independent(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_issue_comments("issue-1")
        await cached.fetch_issue_comments("issue-2")

        assert mock_client.fetch_issue_comments.await_count == 2


# --- invalidate ---


class TestInvalidate:
    @pytest.mark.asyncio()
    async def test_invalidate_specific_key(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_my_issues("team-1")
        cached.invalidate("issues:team-1")
        await cached.fetch_my_issues("team-1")

        assert mock_client.fetch_my_issues.await_count == 2

    @pytest.mark.asyncio()
    async def test_invalidate_all(self, mock_client: MagicMock) -> None:
        _clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=30, _clock=clock_fn)

        await cached.fetch_my_issues("team-1")
        await cached.fetch_issue_by_branch("feat/x")
        cached.invalidate()
        await cached.fetch_my_issues("team-1")
        await cached.fetch_issue_by_branch("feat/x")

        assert mock_client.fetch_my_issues.await_count == 2
        assert mock_client.fetch_issue_by_branch.await_count == 2

    @pytest.mark.asyncio()
    async def test_invalidate_nonexistent_key_is_noop(
        self, mock_client: MagicMock
    ) -> None:
        cached = CachedLinearClient(mock_client)
        cached.invalidate("does-not-exist")  # should not raise


# --- TTL configuration ---


class TestTTLConfig:
    @pytest.mark.asyncio()
    async def test_custom_ttl(self, mock_client: MagicMock) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, ttl_seconds=5, _clock=clock_fn)

        await cached.fetch_my_issues("team-1")
        clock[0] += dt.timedelta(seconds=6)
        await cached.fetch_my_issues("team-1")

        assert mock_client.fetch_my_issues.await_count == 2

    @pytest.mark.asyncio()
    async def test_default_ttl_is_30s(self, mock_client: MagicMock) -> None:
        clock, clock_fn = _controllable_clock()
        cached = CachedLinearClient(mock_client, _clock=clock_fn)

        await cached.fetch_my_issues("team-1")
        clock[0] += dt.timedelta(seconds=29)
        await cached.fetch_my_issues("team-1")

        assert mock_client.fetch_my_issues.await_count == 1


# --- Lifecycle delegation ---


class TestLifecycleDelegation:
    @pytest.mark.asyncio()
    async def test_connect_delegates(self, mock_client: MagicMock) -> None:
        cached = CachedLinearClient(mock_client)
        await cached.connect()
        mock_client.connect.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_close_delegates(self, mock_client: MagicMock) -> None:
        cached = CachedLinearClient(mock_client)
        await cached.close()
        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_context_manager(self, mock_client: MagicMock) -> None:
        async with CachedLinearClient(mock_client) as cached:
            assert isinstance(cached, CachedLinearClient)
        mock_client.connect.assert_awaited_once()
        mock_client.close.assert_awaited_once()
