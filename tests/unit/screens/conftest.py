"""Shared fixtures for screens tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.app import App

from tt_tmux.git.models import WorkingTreeStatus, WorktreeInfo


# ---------------------------------------------------------------------------
# Sample worktree data
# ---------------------------------------------------------------------------


def _make_worktrees() -> list[WorktreeInfo]:
    """Return a realistic list of worktrees for testing."""
    return [
        WorktreeInfo(
            path="/home/user/repos/project",
            head="aabbccdd",
            branch="(bare)",
            is_bare=True,
        ),
        WorktreeInfo(
            path="/home/user/repos/feature-login",
            head="11223344",
            branch="feature/login",
            wt_status=WorkingTreeStatus(staged=1, modified=2),
        ),
        WorktreeInfo(
            path="/home/user/repos/bugfix-nav",
            head="55667788",
            branch="bugfix/nav",
            wt_status=WorkingTreeStatus(),
        ),
    ]


@pytest.fixture
def sample_worktrees() -> list[WorktreeInfo]:
    """A realistic set of worktrees (bare + dirty + clean)."""
    return _make_worktrees()


# ---------------------------------------------------------------------------
# Git operation mocks
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_list_worktrees(sample_worktrees):
    """Patch ``list_worktrees`` in the worktree_list module."""
    with patch(
        "tt_tmux.screens.worktree_list.list_worktrees",
        new_callable=AsyncMock,
        return_value=sample_worktrees,
    ) as mock:
        yield mock


@pytest.fixture
def mock_populate_statuses():
    """Patch ``populate_worktree_statuses`` — a no-op by default."""
    with patch(
        "tt_tmux.screens.worktree_list.populate_worktree_statuses",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Tmux operation mocks
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_tmux_active():
    """Patch ``is_worktree_session_active`` — returns False by default."""
    with patch(
        "tt_tmux.screens.worktree_list.is_worktree_session_active",
        return_value=False,
    ) as mock:
        yield mock


@pytest.fixture
def mock_build_session_config():
    """Patch ``build_session_config``."""
    with patch(
        "tt_tmux.screens.worktree_list.build_session_config",
    ) as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture
def mock_enter_worktree_session():
    """Patch ``enter_worktree_session``."""
    with patch(
        "tt_tmux.screens.worktree_list.enter_worktree_session",
    ) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Composite fixture — patches everything needed for WorktreeListScreen
# ---------------------------------------------------------------------------


@pytest.fixture
def all_screen_mocks(
    mock_list_worktrees,
    mock_populate_statuses,
    mock_tmux_active,
):
    """Activate all mocks needed for a basic WorktreeListScreen test."""
    return {
        "list_worktrees": mock_list_worktrees,
        "populate_statuses": mock_populate_statuses,
        "tmux_active": mock_tmux_active,
    }


# ---------------------------------------------------------------------------
# Screen test app helper
# ---------------------------------------------------------------------------


class ScreenTestApp(App):
    """Minimal host app for pushing a Screen and testing it."""

    CSS = """
    Screen { layout: vertical; }
    #wt-layout { height: 1fr; }
    #wt-table { height: 1fr; }
    #action-bar { height: 3; dock: bottom; }
    #search-bar { height: auto; }
    """

    def __init__(self, screen_factory):
        super().__init__()
        self._screen_factory = screen_factory

    def on_mount(self) -> None:
        self.push_screen(self._screen_factory())


@pytest.fixture
def screen_app():
    """Factory: returns a ScreenTestApp wrapping the given screen factory."""

    def _make(screen_factory):
        return ScreenTestApp(screen_factory)

    return _make


# ---------------------------------------------------------------------------
# Helper — wait for screen to be fully mounted and workers to settle
# ---------------------------------------------------------------------------


async def wait_ready(pilot, app):
    """Pause to let the screen mount, then wait for initial workers."""
    await pilot.pause()
    await pilot.pause()
    await app.workers.wait_for_complete()
