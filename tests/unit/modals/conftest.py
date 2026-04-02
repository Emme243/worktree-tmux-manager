"""Shared fixtures for modal tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App

from tt_tmux.git.models import WorkingTreeStatus, WorktreeInfo


class ModalTestApp(App):
    """Minimal host app for pushing a modal and capturing its result."""

    CSS = """
    ModalScreen { align: center middle; }
    #modal-dialog { width: 60; height: auto; padding: 1 2; }
    """

    def __init__(self, modal):
        super().__init__()
        self._modal = modal
        self.modal_result: bool | None = None

    def on_mount(self) -> None:
        self.push_screen(self._modal, callback=self._on_dismiss)

    def _on_dismiss(self, result: bool | None) -> None:
        self.modal_result = result


@pytest.fixture
def modal_app():
    """Factory: returns a ModalTestApp wrapping the given modal."""

    def _make(modal):
        return ModalTestApp(modal)

    return _make


@pytest.fixture
def mock_list_branches():
    """Patch ``list_branches`` in the add_worktree module."""
    with patch(
        "tt_tmux.modals.add_worktree.list_branches",
        new_callable=AsyncMock,
        return_value=["main", "dev", "feature/login"],
    ) as mock:
        yield mock


@pytest.fixture
def mock_add_worktree():
    """Patch ``add_worktree`` in the add_worktree module."""
    with patch(
        "tt_tmux.modals.add_worktree.add_worktree",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_remove_worktree():
    """Patch ``remove_worktree`` in the remove_worktree module."""
    with patch(
        "tt_tmux.modals.remove_worktree.remove_worktree",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_move_worktree():
    """Patch ``move_worktree`` in the rename_worktree module."""
    with patch(
        "tt_tmux.modals.rename_worktree.move_worktree",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def clean_worktree() -> WorktreeInfo:
    """A worktree with clean working tree status."""
    return WorktreeInfo(
        path="/home/user/repos/my-feature",
        head="abc12345",
        branch="feature/login",
        wt_status=WorkingTreeStatus(),
    )


@pytest.fixture
def dirty_worktree() -> WorktreeInfo:
    """A worktree with uncommitted changes."""
    return WorktreeInfo(
        path="/home/user/repos/my-feature",
        head="abc12345",
        branch="feature/login",
        wt_status=WorkingTreeStatus(staged=1, modified=2),
    )
