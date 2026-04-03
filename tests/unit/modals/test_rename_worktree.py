"""Tests for modules.modals.rename_worktree — RenameWorktreeModal."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from textual.widgets import Button, Input, Label

from modules.git.models import GitError
from modules.modals.rename_worktree import RenameWorktreeModal

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _wait_ready(pilot):
    """Pause to let the modal mount fully."""
    await pilot.pause()
    await pilot.pause()


# ---------------------------------------------------------------------------
# Init / path computation
# ---------------------------------------------------------------------------


class TestRenameWorktreeModalInit:
    def test_stores_current_name(self):
        modal = RenameWorktreeModal("/repo", "/home/user/repos/my-feature")
        assert modal.current_name == "my-feature"

    def test_stores_parent_dir(self):
        modal = RenameWorktreeModal("/repo", "/home/user/repos/my-feature")
        assert modal.parent_dir == "/home/user/repos"

    def test_stores_repo_dir(self):
        modal = RenameWorktreeModal("/repo", "/home/user/repos/my-feature")
        assert modal.repo_dir == "/repo"


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


class TestRenameWorktreeModalCompose:
    async def test_renders_title(self, modal_app):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            titles = app.screen.query(".modal-title")
            assert len(titles) == 1
            assert "Rename Worktree" in titles.first().render().plain

    async def test_input_prefilled_with_current_name(self, modal_app):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            name_input = app.screen.query_one("#new-name", Input)
            assert name_input.value == "my-feature"

    async def test_renders_current_name_label(self, modal_app):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            labels = app.screen.query(Label)
            label_texts = [lbl.render().plain for lbl in labels]
            assert any("my-feature" in t for t in label_texts)

    async def test_renders_buttons(self, modal_app):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            confirm = app.screen.query_one("#confirm-btn", Button)
            cancel = app.screen.query_one("#cancel-btn", Button)
            assert "Rename" in confirm.label.plain
            assert "Cancel" in cancel.label.plain


# ---------------------------------------------------------------------------
# Cancel / dismiss
# ---------------------------------------------------------------------------


class TestRenameWorktreeModalCancel:
    async def test_cancel_button_dismisses_false(self, modal_app):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.click("#cancel-btn")
            await pilot.pause()
            assert app.modal_result is False

    async def test_escape_dismisses_false(self, modal_app):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            await pilot.press("escape")
            await pilot.pause()
            assert app.modal_result is False

    async def test_q_dismisses_false_when_input_not_focused(self, modal_app):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            app.screen.query_one("#cancel-btn").focus()
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
            assert app.modal_result is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestRenameWorktreeModalValidation:
    async def test_empty_name_does_not_rename(self, modal_app, mock_move_worktree):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            app.screen.query_one("#new-name", Input).value = ""
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_move_worktree.assert_not_called()

    async def test_whitespace_only_does_not_rename(self, modal_app, mock_move_worktree):
        app = modal_app(RenameWorktreeModal("/repo", "/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            app.screen.query_one("#new-name", Input).value = "   "
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_move_worktree.assert_not_called()


# ---------------------------------------------------------------------------
# Successful rename
# ---------------------------------------------------------------------------


class TestRenameWorktreeModalRename:
    async def test_rename_calls_move_worktree(self, modal_app, mock_move_worktree):
        app = modal_app(RenameWorktreeModal("/repo", "/home/user/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            app.screen.query_one("#new-name", Input).value = "renamed-feature"
            await pilot.click("#confirm-btn")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_move_worktree.assert_called_once_with(
                "/repo",
                "/home/user/repos/my-feature",
                "/home/user/repos/renamed-feature",
            )
            assert app.modal_result is True

    async def test_input_submitted_triggers_rename(self, modal_app, mock_move_worktree):
        app = modal_app(RenameWorktreeModal("/repo", "/home/user/repos/my-feature"))
        async with app.run_test(size=(100, 40)) as pilot:
            await _wait_ready(pilot)
            name_input = app.screen.query_one("#new-name", Input)
            name_input.value = "renamed-feature"
            name_input.focus()
            await pilot.press("enter")
            await pilot.pause()
            await app.workers.wait_for_complete()
            mock_move_worktree.assert_called_once()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestRenameWorktreeModalErrors:
    async def test_git_error_does_not_dismiss(self, modal_app):
        with patch(
            "modules.modals.rename_worktree.move_worktree",
            new_callable=AsyncMock,
            side_effect=GitError("permission denied"),
        ):
            app = modal_app(RenameWorktreeModal("/repo", "/home/user/repos/my-feature"))
            async with app.run_test(size=(100, 40)) as pilot:
                await _wait_ready(pilot)
                app.screen.query_one("#new-name", Input).value = "renamed"
                await pilot.click("#confirm-btn")
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert app.modal_result is None
