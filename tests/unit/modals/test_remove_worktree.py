"""Tests for tt_tmux.modals.remove_worktree — RemoveWorktreeModal."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from textual.widgets import Button, Label, Static

from tt_tmux.git.models import GitError, WorkingTreeStatus, WorktreeInfo
from tt_tmux.modals.remove_worktree import RemoveWorktreeModal


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _wait_ready(pilot):
    """Pause to let the modal mount fully."""
    await pilot.pause()
    await pilot.pause()


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalCompose:
    async def test_renders_title(self, modal_app, clean_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            titles = app.screen.query(".modal-title")
            assert len(titles) >= 1
            assert "Remove Worktree" in titles.first().render().plain

    async def test_renders_confirmation_with_worktree_name(
        self, modal_app, clean_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            labels = app.screen.query(Label)
            label_texts = [lbl.render().plain for lbl in labels]
            assert any("my-feature" in t for t in label_texts)

    async def test_renders_buttons(self, modal_app, clean_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            confirm = app.screen.query_one("#confirm-btn", Button)
            cancel = app.screen.query_one("#cancel-btn", Button)
            assert "Remove" in confirm.label.plain
            assert "Cancel" in cancel.label.plain

    async def test_no_warning_for_clean_worktree(self, modal_app, clean_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            warnings = app.screen.query(".modal-warning")
            assert len(warnings) == 0

    async def test_warning_shown_for_dirty_worktree(self, modal_app, dirty_worktree):
        app = modal_app(RemoveWorktreeModal("/repo", dirty_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            warnings = app.screen.query(".modal-warning")
            assert len(warnings) == 1

    async def test_no_warning_when_status_is_none(self, modal_app):
        wt = WorktreeInfo(
            path="/home/user/repos/my-feature",
            head="abc12345",
            branch="feature/login",
            wt_status=None,
        )
        app = modal_app(RemoveWorktreeModal("/repo", wt))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            warnings = app.screen.query(".modal-warning")
            assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Cancel / dismiss
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalCancel:
    async def test_cancel_button_dismisses_false(
        self, modal_app, clean_worktree, mock_remove_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#cancel-btn")
            await pilot.pause()
            assert app.modal_result is False

    async def test_escape_dismisses_false(
        self, modal_app, clean_worktree, mock_remove_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("escape")
            await pilot.pause()
            assert app.modal_result is False


# ---------------------------------------------------------------------------
# Confirm removal
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalConfirm:
    async def test_confirm_button_calls_remove(
        self, modal_app, clean_worktree, mock_remove_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once_with(
                "/repo", "/home/user/repos/my-feature", force=True
            )
            assert app.modal_result is True

    async def test_enter_key_triggers_confirm(
        self, modal_app, clean_worktree, mock_remove_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("enter")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once()
            assert app.modal_result is True

    async def test_action_confirm_calls_remove(
        self, modal_app, clean_worktree, mock_remove_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            app.screen.action_confirm()
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once()

    async def test_remove_with_dirty_worktree_still_forces(
        self, modal_app, dirty_worktree, mock_remove_worktree
    ):
        app = modal_app(RemoveWorktreeModal("/repo", dirty_worktree))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_remove_worktree.assert_called_once_with(
                "/repo", "/home/user/repos/my-feature", force=True
            )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRemoveWorktreeModalErrors:
    async def test_git_error_does_not_dismiss(self, modal_app, clean_worktree):
        with patch(
            "tt_tmux.modals.remove_worktree.remove_worktree",
            new_callable=AsyncMock,
            side_effect=GitError("worktree is locked"),
        ):
            app = modal_app(RemoveWorktreeModal("/repo", clean_worktree))
            async with app.run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot)
                await pilot.click("#confirm-btn")
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert app.modal_result is None
